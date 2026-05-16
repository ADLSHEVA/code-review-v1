"""Main code review agent orchestration."""

import json
import logging
import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from ..config import settings
from ..git.models import DiffResult
from ..parsing.context_builder import ContextBuilder
from ..parsing.ast_extractor import CodeContext
from ..output.models import ReviewComment, ReviewReport, Severity, ReviewCategory
from ..output.severity import SeverityClassifier
from ..rag.retriever import GuidelineRetriever
from ..plc.plc_rules import PLCRulesChecker
from ..plc.external_analyzer import ExternalAnalyzer
from ..plc.cfg_analyzer import CFGAnalyzer
from ..plc.st_extractor import StructuredTextExtractor
from ..plc.xml_parser import PLCXmlParser
from ..plc.simatic_parser import SimaticMLParser
from ..plc.twincat_parser import TwincatParser
from ..plc.codesys_parser import CodesysParser
from ..plc.rockwell_parser import RockwellParser
from ..plc.abb_parser import ABBParser
from ..plc.ge_parser import GEParser
from ..plc.omron_parser import OmronParser
from ..plc.ld_converter import LadderDiagramConverter
from ..plc.fbd_converter import FBDConverter
from ..plc.sfc_converter import SFCConverter
from ..plc.hw_config import HWConfigParser, HWConfigRulesChecker
from ..plc.file_support import extract_structured_text, has_plc_project_extension, is_plc_project_file
from ..plc.plc_rules import PLCRuleViolation
from .prompts import SYSTEM_PROMPT, REVIEW_TEMPLATE, SUMMARY_PROMPT
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class CodeReviewAgent:
    """Main code review agent that orchestrates the review pipeline."""

    def __init__(self, model: str | None = None):
        self.model = model or settings.claude_model
        is_mimo = self.model.startswith("mimo")

        llm_kwargs = {
            "model": self.model,
            "temperature": 1.0 if is_mimo else settings.temperature,
            "anthropic_api_key": settings.anthropic_api_key,
            "max_tokens": 4000,
        }
        if settings.anthropic_base_url:
            llm_kwargs["anthropic_api_url"] = settings.anthropic_base_url
        if is_mimo or settings.disable_thinking:
            llm_kwargs["thinking"] = {"type": "disabled"}
        self.llm = ChatAnthropic(**llm_kwargs)
        self.context_builder = ContextBuilder()
        self.severity_classifier = SeverityClassifier()
        self._retriever: GuidelineRetriever | None = None

    @property
    def retriever(self) -> GuidelineRetriever:
        if self._retriever is None:
            self._retriever = GuidelineRetriever()
            self._retriever.ensure_guidelines_indexed()
        return self._retriever

    def review_diff(
        self,
        diff_result: DiffResult,
        repo_path: str,
        progress_callback: callable = None,
    ) -> ReviewReport:
        """Review a diff and produce a structured ReviewReport."""
        contexts = self.context_builder.build_review_context(diff_result, repo_path)
        all_comments: list[ReviewComment] = []
        reviewed_files: list[str] = []
        skipped_files: list[str] = []
        total = len(contexts)

        for i, ctx in enumerate(contexts):
            if progress_callback:
                try:
                    progress_callback(ctx.file_path, i, total)
                except Exception:
                    pass

            try:
                # Run PLC rules checker for Structured Text files
                plc_comments = self._review_plc_file(ctx, repo_path)
                all_comments.extend(plc_comments)

                # Also run LLM review for AI-powered analysis
                rag_context = self._get_rag_context(ctx)
                prompt = self._build_prompt(ctx, rag_context)
                response = self._call_llm(prompt)
                comments = self._parse_response(response, ctx)
                all_comments.extend(comments)
                reviewed_files.append(ctx.file_path)
            except Exception as e:
                logger.warning(f"Failed to review {ctx.file_path}: {e}")
                skipped_files.append(ctx.file_path)

        # Filter and deduplicate
        all_comments = self._filter_comments(all_comments)

        return ReviewReport(
            summary=self._generate_summary(all_comments),
            comments=all_comments,
            stats=self._compute_stats(all_comments),
            reviewed_files=list(set(reviewed_files)),
            skipped_files=skipped_files,
        )

    def review_file_diff(
        self, file_path: str, diff_content: str, source_code: str | None = None
    ) -> list[ReviewComment]:
        """Review a single file's diff content."""
        # Build a minimal context
        ctx = CodeContext(
            file_path=file_path,
            language=self._detect_language(file_path),
            changed_lines=(0, 0),
            enclosing_function=source_code[:5000] if source_code else None,
        )

        rag_context = self._get_rag_context(ctx)
        prompt = self._build_prompt(ctx, rag_context, diff_override=diff_content)
        response = self._call_llm(prompt)
        return self._filter_comments(self._parse_response(response, ctx))

    def _review_plc_file(self, ctx: CodeContext, repo_path: str) -> list[ReviewComment]:
        """Run PLC-specific rules checking on Structured Text files.

        Handles three PLC source formats:
        1. Plain .st files — direct Structured Text
        2. SimaticML XML — Siemens TIA Portal (S7-1200/1500)
        3. TcPOU XML — Beckhoff TwinCAT 3

        For graphical languages (LD/FBD), converts to ST first via LadderDiagramConverter.
        """
        if ctx.language != "structured_text":
            return []

        import os

        full_path = os.path.join(repo_path, ctx.file_path)
        if not os.path.isfile(full_path):
            return []

        source = None
        ld_converted = False

        # Try to extract ST code based on file type
        if has_plc_project_extension(full_path):
            source = extract_structured_text(full_path)
            ld_converted = False
        else:
            # Plain .st file
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    source = f.read()
            except OSError:
                return []

        if not source:
            return []

        # If source contains FBD markers, convert to ST via data flow analysis
        if FBDConverter.has_fbd_marker(source):
            fbd_result = FBDConverter.extract_and_convert(source)
            if fbd_result.st_code:
                source = source + "\n\n// === FBD → ST Conversion ===\n" + fbd_result.st_code
                ld_converted = True

        # If source contains LD markers, convert to ST via relay logic
        if LadderDiagramConverter.has_graphical_language(source):
            conversion = LadderDiagramConverter.extract_and_convert(source)
            if conversion.st_code:
                source = source + "\n\n// === LD → ST Conversion ===\n" + conversion.st_code
                ld_converted = True

        # If source contains SFC markers, convert to ST state machine
        if SFCConverter.has_sfc_marker(source):
            sfc_result = SFCConverter.extract_and_convert(source)
            if sfc_result.st_code:
                source = source + "\n\n// === SFC → ST State Machine ===\n" + sfc_result.st_code

        # Run PLC rules checker
        violations = PLCRulesChecker.check_code(source)

        # Run external tools if available (IEC Checker, plc-lint, etc.)
        try:
            ext_analyzer = ExternalAnalyzer()
            ext_violations = ext_analyzer.analyze(full_path, source)
            violations.extend(ext_violations)
        except Exception as e:
            logger.debug(f"External analyzer failed: {e}")

        # Run CFG-based analysis (unreachable code, loops, def-use, complexity)
        try:
            cfg_findings = CFGAnalyzer.analyze(source)
            for finding in cfg_findings:
                violations.append(PLCRuleViolation(
                    rule_id=finding.get("rule_id", "CFG-???"),
                    rule_name=finding.get("rule_name", "CFG finding"),
                    severity=finding.get("severity", "warning"),
                    description=finding.get("description", ""),
                    line_number=finding.get("line_number"),
                ))
        except Exception as e:
            logger.debug(f"CFG analysis failed: {e}")

        # Run hardware configuration analysis (TIA Portal HWConfig XML)
        hw_comments = []
        if full_path.lower().endswith(".xml"):
            try:
                hw_comments = self._review_hw_config(full_path, ctx)
            except Exception as e:
                logger.debug(f"HW config analysis failed: {e}")

        # Convert PLCRuleViolation to ReviewComment
        severity_map = {
            "critical": Severity.CRITICAL,
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "info": Severity.INFO,
        }

        category_map = {
            "critical": ReviewCategory.SECURITY,
            "error": ReviewCategory.POTENTIAL_BUG,
            "warning": ReviewCategory.POTENTIAL_BUG,
            "info": ReviewCategory.CONVENTION,
        }

        comments = []
        for v in violations:
            comments.append(ReviewComment(
                file_path=ctx.file_path,
                line_start=v.line_number or 1,
                severity=severity_map.get(v.severity, Severity.WARNING),
                category=category_map.get(v.severity, ReviewCategory.POTENTIAL_BUG),
                title=v.rule_name,
                description=f"[{v.rule_id}] {v.description}",
                suggestion=v.suggestion,
                confidence=0.9,
            ))

        comments.extend(hw_comments)
        return comments

    def _extract_st_from_xml(self, xml_path: str) -> tuple[str | None, bool]:
        """Extract ST code from PLC XML files.

        Tries SimaticML → TwinCAT → CODESYS → generic PLC XML.
        Returns (source_code, was_ld_converted).
        """
        import os

        # Try SimaticML (Siemens TIA Portal)
        if SimaticMLParser.is_simaticml(xml_path):
            block = SimaticMLParser.parse_file(xml_path)
            if block:
                if block.source_code:
                    return block.source_code, False
                all_code = []
                for net in block.networks:
                    if net.source_code:
                        all_code.append(net.source_code)
                if all_code:
                    return "\n\n".join(all_code), False

        # Try TwinCAT TcPOU (Beckhoff)
        if TwincatParser.is_twincat(xml_path):
            project = TwincatParser.parse_file(xml_path)
            if project:
                parts = []
                for pou in project.pous:
                    if pou.implementation:
                        parts.append(f"// {pou.pou_type} {pou.name}")
                        parts.append(pou.implementation)
                if parts:
                    return "\n\n".join(parts), False

        # Try CODESYS (WAGO, Schneider, ABB, Bosch Rexroth, etc.)
        if CodesysParser.is_codesys(xml_path):
            project = CodesysParser.parse_file(xml_path)
            if project:
                parts = []
                for pou in project.all_pous:
                    if pou.implementation and not pou.implementation.startswith("["):
                        parts.append(f"// {pou.pou_type} {pou.name}")
                        parts.append(pou.implementation)
                if parts:
                    return "\n\n".join(parts), False

        # Try Rockwell/Allen-Bradley L5X
        if RockwellParser.is_l5x(xml_path):
            project = RockwellParser.parse_file(xml_path)
            if project:
                parts = []
                for routine in project.all_routines:
                    if routine.routine_type == "ST" and routine.st_code:
                        parts.append(f"// Routine: {routine.name}")
                        parts.append(routine.st_code)
                    elif routine.routine_type == "RLL" and routine.rungs:
                        parts.append(f"// Routine: {routine.name} (Ladder → ST)")
                        parts.append(RockwellParser._rungs_to_pseudo_st(routine.rungs))
                if parts:
                    return "\n\n".join(parts), False

        # Try ABB Automation Builder
        if ABBParser.is_abb(xml_path):
            project = ABBParser.parse_file(xml_path)
            if project:
                parts = []
                for block in project.all_blocks:
                    if block.source_code and not block.source_code.startswith("["):
                        parts.append(f"// {block.block_type} {block.name}")
                        parts.append(block.source_code)
                if parts:
                    return "\n\n".join(parts), False

        # Try GE/Fanuc Proficy Machine Edition
        if GEParser.is_ge(xml_path):
            project = GEParser.parse_file(xml_path)
            if project:
                parts = []
                for block in project.all_blocks:
                    if block.source_code and not block.source_code.startswith("["):
                        parts.append(f"// {block.block_type} {block.name}")
                        parts.append(block.source_code)
                if parts:
                    return "\n\n".join(parts), False

        # Try Omron Sysmac Studio
        if OmronParser.is_omron(xml_path):
            project = OmronParser.parse_file(xml_path)
            if project:
                parts = []
                for block in project.all_blocks:
                    if block.source_code and not block.source_code.startswith("["):
                        parts.append(f"// {block.block_type} {block.name}")
                        parts.append(block.source_code)
                if parts:
                    return "\n\n".join(parts), False

        # Fallback: generic PLC XML parser
        block = PLCXmlParser.parse_file(xml_path)
        if block and block.source_code:
            return block.source_code, False

        return None, False

    def _review_hw_config(self, xml_path: str, ctx: CodeContext) -> list[ReviewComment]:
        """Parse and validate TIA Portal hardware configuration."""
        if not HWConfigParser.is_hwconfig(xml_path):
            return []

        config = HWConfigParser.parse_file(xml_path)
        if not config:
            return []

        violations = HWConfigRulesChecker.check(config)
        if not violations:
            return []

        severity_map = {
            "critical": Severity.CRITICAL,
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "info": Severity.INFO,
        }
        category_map = {
            "critical": ReviewCategory.SECURITY,
            "error": ReviewCategory.SECURITY,
            "warning": ReviewCategory.SECURITY,
            "info": ReviewCategory.CONVENTION,
        }

        return [
            ReviewComment(
                file_path=ctx.file_path,
                line_start=1,
                severity=severity_map.get(v.severity, Severity.WARNING),
                category=category_map.get(v.severity, ReviewCategory.SECURITY),
                title=f"[{v.rule_id}] {v.rule_name}",
                description=f"[{v.component}] {v.description}",
                suggestion=v.suggestion,
                confidence=0.95,
            )
            for v in violations
        ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with retry logic."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = self.llm.invoke(messages)
        return self._extract_text(response.content)

    @staticmethod
    def _extract_text(content) -> str:
        """Extract plain text from LLM response content.

        Handles both string responses (Anthropic Claude) and list-of-blocks
        responses (Mimo and other compatible providers that include thinking blocks).
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return "\n".join(parts)
        return str(content)

    def _build_prompt(
        self,
        ctx: CodeContext,
        rag_context: str,
        diff_override: str | None = None,
    ) -> str:
        """Build the review prompt for a code context."""
        # Use full source + diff if available, otherwise fall back to enclosing function
        full_source = ctx.full_source
        diff_text = ctx.diff_text

        if diff_override:
            diff_content = diff_override
        elif diff_text:
            diff_content = diff_text
        elif ctx.enclosing_function:
            diff_content = ctx.enclosing_function
        else:
            diff_content = f"# Changed lines {ctx.changed_lines[0]}-{ctx.changed_lines[1]}"

        # Use full source as the enclosing function context if available
        function_context = full_source if full_source else (ctx.enclosing_function or "N/A")

        return REVIEW_TEMPLATE.format(
            file_path=ctx.file_path,
            language=ctx.language or "unknown",
            diff_content=diff_content,
            enclosing_function=function_context,
            enclosing_class=ctx.enclosing_class or "N/A",
            imports="\n".join(ctx.imports) if ctx.imports else "N/A",
            rag_context=rag_context,
        )

    def _get_rag_context(self, ctx: CodeContext) -> str:
        """Retrieve relevant guidelines from RAG."""
        try:
            query_parts = [ctx.language or "", "coding guidelines"]
            if ctx.function_name:
                query_parts.append(f"function {ctx.function_name}")
            query = " ".join(query_parts)

            results = self.retriever.search(query, k=3)
            if not results:
                return ""

            guidelines = "\n\n".join([
                f"### Relevant Guideline:\n{doc.page_content}"
                for doc in results
            ])
            return f"\n### Project Guidelines:\n{guidelines}\n"
        except Exception:
            return ""

    def _parse_response(
        self, response_text: str, ctx: CodeContext
    ) -> list[ReviewComment]:
        """Parse LLM JSON response into ReviewComment objects."""
        # Extract JSON from response (handle markdown code blocks)
        json_str = self._extract_json(response_text)
        if not json_str:
            return []

        try:
            raw_comments = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response for {ctx.file_path}")
            return []

        if not isinstance(raw_comments, list):
            return []

        comments = []
        for raw in raw_comments:
            try:
                # Ensure file_path is set
                if "file_path" not in raw or not raw["file_path"]:
                    raw["file_path"] = ctx.file_path

                comment = ReviewComment(**raw)

                # Validate confidence threshold
                if comment.confidence < settings.confidence_threshold:
                    continue

                # Apply keyword-based severity escalation
                escalated = self.severity_classifier.classify(
                    comment.category, comment.description, comment.severity
                )
                if escalated != comment.severity:
                    logger.debug(
                        f"Severity escalated: {comment.severity} -> {escalated} "
                        f"for '{comment.title}' (keyword match)"
                    )
                    comment = comment.model_copy(update={"severity": escalated})

                # Apply confidence-based severity validation
                validated = self.severity_classifier.validate_severity(
                    comment.severity, comment.category, comment.confidence
                )
                if validated != comment.severity:
                    logger.debug(
                        f"Severity downgraded: {comment.severity} -> {validated} "
                        f"for '{comment.title}' (confidence={comment.confidence})"
                    )
                    comment = comment.model_copy(update={"severity": validated})

                comments.append(comment)
            except Exception as e:
                logger.debug(f"Skipping invalid comment: {e}")
                continue

        return comments

    @staticmethod
    def _extract_json(text: str) -> str | None:
        """Extract JSON array from text that may contain markdown code blocks."""
        # Try to find JSON in code blocks
        json_block_pattern = re.compile(r"```(?:json)?\s*\n?(\[.*?\])\s*\n?```", re.DOTALL)
        match = json_block_pattern.search(text)
        if match:
            return match.group(1)

        # Try to find a raw JSON array
        array_pattern = re.compile(r"\[.*\]", re.DOTALL)
        match = array_pattern.search(text)
        if match:
            return match.group(0)

        return None

    def _filter_comments(self, comments: list[ReviewComment]) -> list[ReviewComment]:
        """Filter and deduplicate comments."""
        seen = set()
        filtered = []
        for comment in comments:
            # Deduplicate by (file, line, title)
            key = (comment.file_path, comment.line_start, comment.title)
            if key in seen:
                continue
            seen.add(key)
            filtered.append(comment)

        # Sort by severity (critical first) then by file and line
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.ERROR: 1,
            Severity.WARNING: 2,
            Severity.INFO: 3,
        }
        filtered.sort(key=lambda c: (severity_order.get(c.severity, 99), c.file_path, c.line_start))
        return filtered

    def _generate_summary(self, comments: list[ReviewComment]) -> str:
        """Generate a human-readable summary of findings."""
        if not comments:
            return "No issues found. The code looks good!"

        counts = self._compute_stats(comments)
        parts = []
        if counts.get("critical", 0):
            parts.append(f"{counts['critical']} critical")
        if counts.get("error", 0):
            parts.append(f"{counts['error']} errors")
        if counts.get("warning", 0):
            parts.append(f"{counts['warning']} warnings")
        if counts.get("info", 0):
            parts.append(f"{counts['info']} info")

        summary = f"Found {len(comments)} issue(s): {', '.join(parts)}."

        # Add category breakdown
        categories = {}
        for c in comments:
            categories[c.category.value] = categories.get(c.category.value, 0) + 1
        if categories:
            cat_parts = [f"{v} {k}" for k, v in sorted(categories.items(), key=lambda x: -x[1])]
            summary += f" Categories: {', '.join(cat_parts)}."

        return summary

    @staticmethod
    def _compute_stats(comments: list[ReviewComment]) -> dict[str, int]:
        """Count issues by severity and category."""
        stats: dict[str, int] = {}
        for c in comments:
            stats[c.severity.value] = stats.get(c.severity.value, 0) + 1
            stats[f"cat_{c.category.value}"] = stats.get(f"cat_{c.category.value}", 0) + 1
        return stats

    @staticmethod
    def _detect_language(file_path: str) -> str | None:
        import os
        _, ext = os.path.splitext(file_path)
        lang = settings.language_map.get(ext.lower())
        if lang:
            return lang
        if has_plc_project_extension(file_path) and is_plc_project_file(file_path):
            return "structured_text"
        return None
