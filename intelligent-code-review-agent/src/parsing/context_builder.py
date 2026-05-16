"""Build review context by combining diff and AST information."""

import os

from ..git.models import DiffResult, ChangedFile
from .ast_extractor import ASTExtractor, CodeContext
from ..config import settings
from ..plc.file_support import extract_structured_text, has_plc_project_extension
from ..plc.ld_converter import LadderDiagramConverter
from ..plc.fbd_converter import FBDConverter


class ContextBuilder:
    """Builds review context from diff results and AST extraction."""

    def __init__(self):
        self.ast_extractor = ASTExtractor()

    def build_review_context(
        self, diff_result: DiffResult, repo_path: str
    ) -> list[CodeContext]:
        """For each changed file, build a review context with full file content."""
        contexts = []

        for changed_file in diff_result.files:
            if changed_file.language is None:
                continue

            # Read the full file content
            source = self._read_file(repo_path, changed_file.file_path)
            if source is None:
                source = changed_file.new_content
            if source is None:
                continue

            # Build the diff text for this file
            diff_text = self._build_diff_text(changed_file)

            # Get the range of all changed lines
            all_ranges = [h.changed_range_new for h in changed_file.hunks]
            if all_ranges:
                min_line = min(r[0] for r in all_ranges)
                max_line = max(r[1] for r in all_ranges)
                changed_lines = (min_line, max_line)
            else:
                changed_lines = (1, 1)

            # Extract AST context for the whole file
            ctx = self.ast_extractor.extract_context(
                source_code=source,
                language=changed_file.language,
                changed_lines=changed_lines,
                file_path=changed_file.file_path,
            )

            # Add the full source code and diff to the context
            ctx = ctx.model_copy(update={
                "full_source": source,
                "diff_text": diff_text,
            })

            ctx = self._truncate_context(ctx)
            contexts.append(ctx)

        return contexts

    def _build_diff_text(self, changed_file: ChangedFile) -> str:
        """Build a unified diff text string from a ChangedFile."""
        parts = []
        for hunk in changed_file.hunks:
            parts.append(
                f"@@ -{hunk.old_start},{hunk.old_count} +{hunk.new_start},{hunk.new_count} @@"
            )
            for line in hunk.lines:
                if line.is_added:
                    parts.append(f"+{line.content}")
                elif line.is_deleted:
                    parts.append(f"-{line.content}")
                else:
                    parts.append(f" {line.content}")
        return "\n".join(parts)

    def _read_file(self, repo_path: str, file_path: str) -> str | None:
        """Read file content from the repository.

        For PLC XML files (.xml with SimaticML/TcPOU content), extracts the
        Structured Text source code instead of returning raw XML.
        Tries SimaticML (Siemens) first, then TwinCAT (Beckhoff), then generic.
        """
        full_path = os.path.join(repo_path, file_path)
        if not os.path.isfile(full_path):
            return None
        try:
            # Try to extract ST from PLC XML files
            if has_plc_project_extension(full_path):
                source = extract_structured_text(full_path)
                if source:
                    return source

            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()

            # If it's a .st file, convert graphical markers if present
            if file_path.lower().endswith((".st", ".iecst")):
                if FBDConverter.has_fbd_marker(source):
                    fbd_result = FBDConverter.extract_and_convert(source)
                    if fbd_result.st_code:
                        source += "\n\n// === FBD → ST ===\n" + fbd_result.st_code
                if LadderDiagramConverter.has_graphical_language(source):
                    conversion = LadderDiagramConverter.extract_and_convert(source)
                    if conversion.st_code:
                        source += "\n\n// === LD → ST ===\n" + conversion.st_code

            return source
        except (OSError, UnicodeDecodeError):
            return None

    def _truncate_context(self, context: CodeContext) -> CodeContext:
        """If context is too large, truncate by dropping less important parts."""
        token_count = self._estimate_tokens(context)
        max_tokens = settings.max_context_tokens

        if token_count > max_tokens:
            context = context.model_copy(update={"enclosing_class": None})

        if self._estimate_tokens(context) > max_tokens:
            context = context.model_copy(update={"imports": []})

        if self._estimate_tokens(context) > max_tokens:
            if context.enclosing_function and len(context.enclosing_function) > max_tokens * 3:
                context = context.model_copy(
                    update={"enclosing_function": context.enclosing_function[:max_tokens * 3] + "\n... (truncated)"}
                )

        # Truncate full_source if still too large
        if self._estimate_tokens(context) > max_tokens:
            full_source = context.full_source
            if full_source and len(full_source) > max_tokens * 4:
                context = context.model_copy(
                    update={"full_source": full_source[:max_tokens * 4] + "\n... (truncated)"}
                )

        return context

    def _estimate_tokens(self, context: CodeContext) -> int:
        """Rough token estimate (1 token ~= 4 chars)."""
        total = 0
        if context.enclosing_function:
            total += len(context.enclosing_function)
        if context.enclosing_class:
            total += len(context.enclosing_class)
        total += sum(len(imp) for imp in context.imports)
        total += sum(len(sym) for sym in context.related_symbols)
        # Include full_source in estimate
        if context.full_source:
            total += len(context.full_source)
        if context.diff_text:
            total += len(context.diff_text)
        return total // 4
