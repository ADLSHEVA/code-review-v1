"""Generate fine-tuning datasets for PLC code review LLMs.

Creates training data from:
  - Existing PLC rules (each rule → violation/fixed code pairs)
  - Vulnerability database (CWE-mapped patterns)
  - Real codebases (scan + analyze → training pairs)
  - Curated few-shot examples

Export formats: JSONL (OpenAI/Anthropic), Alpaca, ShareGPT.
"""

import json
import logging
import os
import random
from pathlib import Path

from pydantic import BaseModel

from ..plc_rules import PLCRulesChecker, PLCRuleViolation
from ..cfg_analyzer import CFGAnalyzer
from .domain_context import DomainContext, FewShotExample

logger = logging.getLogger(__name__)


class FineTuneExample(BaseModel):
    """A single fine-tuning training example."""
    instruction: str       # System/user instruction
    input: str             # Code or context to analyze
    output: str            # Expected review output (JSON)
    metadata: dict = {}    # rule_id, severity, category, vendor, source


class DatasetStats(BaseModel):
    """Statistics about a generated dataset."""
    total_examples: int
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_source: dict[str, int] = {}
    train_size: int = 0
    val_size: int = 0
    test_size: int = 0


class DatasetGenerator:
    """Generate fine-tuning datasets for PLC code review."""

    def __init__(self):
        self.domain = DomainContext()

    def generate_from_rules(self) -> list[FineTuneExample]:
        """Synthesize training examples from PLCRulesChecker rules.

        For each rule, generates:
        - A code snippet that violates the rule
        - The expected review finding (JSON)
        - The fixed version of the code
        """
        examples = []

        # Rule-specific code pairs (violation → fix)
        rule_examples = {
            "PLC-001": [
                {
                    "bad": '%Q0.0 := Start AND NOT Stop;',
                    "good": 'o_Motor := Start AND NOT Stop;',
                    "desc": "Direct I/O address in program body",
                },
                {
                    "bad": 'IF %I0.3 THEN\n    %Q0.1 := TRUE;\nEND_IF;',
                    "good": 'IF i_Sensor THEN\n    o_Valve := TRUE;\nEND_IF;',
                    "desc": "Direct I/O in conditional logic",
                },
            ],
            "PLC-003": [
                {
                    "bad": 'IF Speed > 1500 THEN\n    Motor := FALSE;\nEND_IF;',
                    "good": 'VAR CONSTANT MAX_SPEED : INT := 1500; END_VAR\nIF Speed > MAX_SPEED THEN\n    Motor := FALSE;\nEND_IF;',
                    "desc": "Magic number 1500",
                },
                {
                    "bad": 'Timer(IN := TRUE, PT := 100);',
                    "good": 'VAR CONSTANT DELAY_TIME : TIME := T#100MS; END_VAR\nTimer(IN := TRUE, PT := DELAY_TIME);',
                    "desc": "Magic number in timer",
                },
            ],
            "PLC-006": [
                {
                    "bad": 'Result := Numerator / Divisor;',
                    "good": 'IF ABS(Divisor) > 0.001 THEN\n    Result := Numerator / Divisor;\nELSE\n    Result := 0.0;\nEND_IF;',
                    "desc": "Division without zero check",
                },
            ],
            "PLC-004": [
                {
                    "bad": 'Data[Index] := 42;',
                    "good": 'IF (Index >= 0) AND (Index <= 99) THEN\n    Data[Index] := 42;\nEND_IF;',
                    "desc": "Array access without bounds check",
                },
            ],
            "PLC-020": [
                {
                    "bad": 'IF Error THEN\n    GOTO ErrorHandler;\nEND_IF;',
                    "good": 'IF Error THEN\n    HandleError();\nEND_IF;',
                    "desc": "GOTO statement usage",
                },
            ],
            "PLC-007": [
                {
                    "bad": 'Motor := StartButton;',
                    "good": 'Motor := StartButton AND NOT StopButton AND SafetyOK AND NOT ThermalTrip;',
                    "desc": "Output without safety interlock",
                },
            ],
            "PLC-011": [
                {
                    "bad": 'IF Temp = 25.0 THEN\n    Status := "Normal";\nEND_IF;',
                    "good": 'IF ABS(Temp - 25.0) < 0.01 THEN\n    Status := "Normal";\nEND_IF;',
                    "desc": "Floating point equality comparison",
                },
            ],
            "PLC-021": [
                {
                    "bad": 'IF Condition THEN\n    // empty\nEND_IF;',
                    "good": '// Remove empty branch or add logic',
                    "desc": "Empty IF branch",
                },
            ],
            "PLC-009": [
                {
                    "bad": 'PROGRAM MachineControl\nVAR\n    Motor AT %Q0.0 : BOOL;\nEND_VAR\nMotor := Running;',
                    "good": 'PROGRAM MachineControl\nVAR\n    Motor AT %Q0.0 : BOOL;\n    EStop AT %I0.0 : BOOL;\nEND_VAR\nMotor := Running AND EStop;',
                    "desc": "Physical output without E-stop check",
                },
            ],
            "PLC-013": [
                {
                    "bad": 'VAR\n    speed : INT;\n    flag : BOOL;\nEND_VAR',
                    "good": 'VAR\n    i_ConveyorSpeed : INT;  // Input: conveyor speed sensor\n    o_MotorRunning : BOOL;  // Output: motor contactor\nEND_VAR',
                    "desc": "Variables not following naming convention",
                },
            ],
        }

        for rule_id, code_pairs in rule_examples.items():
            for pair in code_pairs:
                # Find the rule info
                violations = PLCRulesChecker.check_code(pair["bad"])
                matching = [v for v in violations if v.rule_id == rule_id]
                violation = matching[0] if matching else PLCRuleViolation(
                    rule_id=rule_id, rule_name=pair["desc"],
                    severity="warning", description=pair["desc"],
                )

                review_json = json.dumps([{
                    "file_path": "example.st",
                    "line_start": 1,
                    "line_end": 1,
                    "severity": violation.severity,
                    "category": "POTENTIAL_BUG",
                    "title": violation.rule_name,
                    "description": violation.description,
                    "suggestion": f"Fix: {pair['good'][:100]}...",
                    "confidence": 0.9,
                }], indent=2)

                examples.append(FineTuneExample(
                    instruction="Review this IEC 61131-3 Structured Text code for issues.",
                    input=f"```st\n{pair['bad']}\n```",
                    output=review_json,
                    metadata={
                        "rule_id": rule_id,
                        "severity": violation.severity,
                        "source": "rules",
                        "has_fix": True,
                    },
                ))

        return examples

    def generate_from_vulnerability_db(self) -> list[FineTuneExample]:
        """Generate training examples from the vulnerability pattern database."""
        examples = []
        patterns = self.domain.get_vulnerability_patterns()

        for pattern in patterns:
            review_json = json.dumps([{
                "file_path": "example.st",
                "line_start": 1,
                "line_end": 1,
                "severity": pattern.severity,
                "category": "PLC_SECURITY",
                "title": pattern.name,
                "description": f"[{pattern.cwe_id}] {pattern.description}",
                "suggestion": f"See fixed example: {pattern.example_fixed[:100]}...",
                "confidence": 0.85,
            }], indent=2)

            examples.append(FineTuneExample(
                instruction="Review this Structured Text code for security vulnerabilities.",
                input=f"```st\n{pattern.example_vulnerable}\n```",
                output=review_json,
                metadata={
                    "cwe_id": pattern.cwe_id,
                    "severity": pattern.severity,
                    "source": "vulnerability_db",
                    "has_fix": True,
                },
            ))

            # Also generate the fixed version as a "clean" example
            examples.append(FineTuneExample(
                instruction="Review this Structured Text code for security vulnerabilities.",
                input=f"```st\n{pattern.example_fixed}\n```",
                output="[]",
                metadata={
                    "cwe_id": pattern.cwe_id,
                    "severity": "clean",
                    "source": "vulnerability_db_clean",
                    "has_fix": False,
                },
            ))

        return examples

    def generate_from_few_shot(self) -> list[FineTuneExample]:
        """Generate training examples from curated few-shot examples."""
        examples = []
        few_shots = self.domain.get_few_shot_examples()

        for fs in few_shots:
            examples.append(FineTuneExample(
                instruction=fs.instruction,
                input=f"```st\n{fs.bad_code}\n```",
                output=fs.review_comment,
                metadata={
                    "rule_id": fs.rule_id,
                    "category": fs.category,
                    "source": "few_shot",
                    "has_fix": True,
                    "fixed_code": fs.fixed_code,
                },
            ))

        return examples

    def generate_from_codebase(self, repo_path: str) -> list[FineTuneExample]:
        """Scan a codebase and generate training pairs from real findings."""
        examples = []
        plc_extensions = {".st", ".iecst", ".xml"}

        for root, dirs, files in os.walk(repo_path):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in plc_extensions:
                    continue

                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                except OSError:
                    continue

                if not source.strip():
                    continue

                # Run rule checker
                violations = PLCRulesChecker.check_code(source)

                # Run CFG analysis
                try:
                    cfg_findings = CFGAnalyzer.analyze(source)
                    for finding in cfg_findings:
                        violations.append(PLCRuleViolation(
                            rule_id=finding.get("rule_id", "CFG"),
                            rule_name=finding.get("rule_name", "CFG"),
                            severity=finding.get("severity", "warning"),
                            description=finding.get("description", ""),
                            line_number=finding.get("line_number"),
                        ))
                except Exception:
                    pass

                if not violations:
                    # Clean code example
                    examples.append(FineTuneExample(
                        instruction="Review this IEC 61131-3 Structured Text code for issues.",
                        input=f"```st\n{source[:3000]}\n```",
                        output="[]",
                        metadata={
                            "source": "codebase",
                            "file": fpath,
                            "severity": "clean",
                        },
                    ))
                else:
                    review_json = json.dumps([{
                        "file_path": fname,
                        "line_start": v.line_number or 1,
                        "line_end": v.line_number or 1,
                        "severity": v.severity,
                        "category": "POTENTIAL_BUG",
                        "title": v.rule_name,
                        "description": f"[{v.rule_id}] {v.description}",
                        "suggestion": v.suggestion or "",
                        "confidence": 0.85,
                    } for v in violations[:10]], indent=2)

                    examples.append(FineTuneExample(
                        instruction="Review this IEC 61131-3 Structured Text code for issues.",
                        input=f"```st\n{source[:3000]}\n```",
                        output=review_json,
                        metadata={
                            "source": "codebase",
                            "file": fpath,
                            "violation_count": len(violations),
                            "severity": violations[0].severity,
                        },
                    ))

        return examples

    def generate_all(self, repo_path: str | None = None) -> list[FineTuneExample]:
        """Generate all available training examples."""
        examples = []
        examples.extend(self.generate_from_rules())
        examples.extend(self.generate_from_vulnerability_db())
        examples.extend(self.generate_from_few_shot())

        if repo_path and os.path.isdir(repo_path):
            examples.extend(self.generate_from_codebase(repo_path))

        random.shuffle(examples)
        return examples

    def export_jsonl(self, examples: list[FineTuneExample], output_path: str) -> str:
        """Export in OpenAI/Anthropic fine-tuning JSONL format.

        Format: {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        system_prompt = self.domain.get_review_guidelines()
        system_text = "You are an expert IEC 61131-3 code reviewer. Review the provided Structured Text code and return findings as a JSON array."

        with open(output_path, "w", encoding="utf-8") as f:
            for ex in examples:
                record = {
                    "messages": [
                        {"role": "system", "content": system_text},
                        {"role": "user", "content": f"{ex.instruction}\n\n{ex.input}"},
                        {"role": "assistant", "content": ex.output},
                    ]
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return output_path

    def export_alpaca(self, examples: list[FineTuneExample], output_path: str) -> str:
        """Export in Alpaca format."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        records = []
        for ex in examples:
            records.append({
                "instruction": ex.instruction,
                "input": ex.input,
                "output": ex.output,
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

        return output_path

    def export_sharegpt(self, examples: list[FineTuneExample], output_path: str) -> str:
        """Export in ShareGPT format."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        conversations = []
        for ex in examples:
            conversations.append({
                "conversations": [
                    {"from": "system", "value": "You are an expert IEC 61131-3 code reviewer."},
                    {"from": "human", "value": f"{ex.instruction}\n\n{ex.input}"},
                    {"from": "gpt", "value": ex.output},
                ],
            })

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(conversations, f, ensure_ascii=False, indent=2)

        return output_path

    def split_dataset(
        self,
        examples: list[FineTuneExample],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        seed: int = 42,
    ) -> tuple[list[FineTuneExample], list[FineTuneExample], list[FineTuneExample]]:
        """Split dataset into train/val/test sets."""
        random.seed(seed)
        shuffled = list(examples)
        random.shuffle(shuffled)

        n = len(shuffled)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]

    def get_stats(self, examples: list[FineTuneExample]) -> DatasetStats:
        """Compute statistics about the dataset."""
        stats = DatasetStats(total_examples=len(examples))

        for ex in examples:
            sev = ex.metadata.get("severity", "unknown")
            stats.by_severity[sev] = stats.by_severity.get(sev, 0) + 1

            source = ex.metadata.get("source", "unknown")
            stats.by_source[source] = stats.by_source.get(source, 0) + 1

        return stats
