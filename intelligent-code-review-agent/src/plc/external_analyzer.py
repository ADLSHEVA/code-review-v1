"""External PLC static analysis tool integration layer.

Provides a unified interface to call external PLC analysis tools as
subprocesses, parse their output, and merge findings into the review pipeline.

Supported tools:
  - IEC Checker (github.com/riebl/iec-checker) — IEC 61131-3 compliance
  - plc-lint — Lightweight ST linter
  - CODESYS CLI — CODESYS command-line analysis (if available)
  - Custom tools — Any tool that outputs JSON or line-based warnings

Usage:
  analyzer = ExternalAnalyzer()
  violations = analyzer.analyze("path/to/program.st")
"""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from .plc_rules import PLCRuleViolation

logger = logging.getLogger(__name__)


class ExternalTool(ABC):
    """Base class for external PLC analysis tool adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for display."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the tool is installed and accessible."""
        ...

    @abstractmethod
    def analyze(self, file_path: str, source_code: str | None = None) -> list[PLCRuleViolation]:
        """Run analysis and return violations."""
        ...

    def _write_temp_st(self, source_code: str, suffix: str = ".st") -> str:
        """Write source code to a temporary .st file for tools that need files."""
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="plc_review_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(source_code)
        except Exception:
            os.close(fd)
            raise
        return tmp_path


class IECCheckerTool(ExternalTool):
    """Adapter for IEC Checker (github.com/riebl/iec-checker).

    IEC Checker performs static analysis on IEC 61131-3 programs:
    - Syntax validation against IEC 61131-3 standard
    - Type checking
    - Dead code detection
    - Unused variable detection
    - PLCopen coding guideline compliance

    Expected CLI usage:
      iec-checker [--format json] <file.st>

    Output format (JSON):
      [{"severity": "warning", "line": 10, "column": 5,
        "message": "...", "rule": "PLC-R3.1"}]
    """

    @property
    def name(self) -> str:
        return "IEC Checker"

    def is_available(self) -> bool:
        return shutil.which("iec-checker") is not None

    def analyze(self, file_path: str, source_code: str | None = None) -> list[PLCRuleViolation]:
        if not self.is_available():
            return []

        tmp_file = None
        try:
            # If source_code provided, write to temp file
            if source_code and not os.path.isfile(file_path):
                tmp_file = self._write_temp_st(source_code)
                file_path = tmp_file

            # Try JSON output first
            result = subprocess.run(
                ["iec-checker", "--format", "json", file_path],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )

            if result.returncode == 0 or result.stdout:
                return self._parse_json_output(result.stdout)

            # Fallback: try plain text output
            result = subprocess.run(
                ["iec-checker", file_path],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )

            return self._parse_text_output(result.stdout)

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"IEC Checker failed: {e}")
            return []
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)

    def _parse_json_output(self, output: str) -> list[PLCRuleViolation]:
        """Parse JSON output from IEC Checker."""
        violations = []
        try:
            findings = json.loads(output)
            if not isinstance(findings, list):
                findings = [findings]

            for finding in findings:
                severity = finding.get("severity", "warning").lower()
                violations.append(PLCRuleViolation(
                    rule_id=finding.get("rule", "IEC-UNKNOWN"),
                    rule_name=finding.get("rule", "IEC Checker finding"),
                    severity=severity,
                    description=finding.get("message", ""),
                    line_number=finding.get("line"),
                    suggestion=finding.get("fix"),
                ))
        except json.JSONDecodeError:
            pass
        return violations

    def _parse_text_output(self, output: str) -> list[PLCRuleViolation]:
        """Parse text output from IEC Checker.

        Expected format: file.st:10:5: warning: message [rule]
        """
        violations = []
        pattern = re.compile(
            r"(?:.+?):(\d+)(?::(\d+))?\s*:\s*(warning|error|info)\s*:\s*(.+?)(?:\s*\[(.+?)\])?$",
            re.IGNORECASE,
        )
        for line in output.split("\n"):
            match = pattern.match(line.strip())
            if match:
                violations.append(PLCRuleViolation(
                    rule_id=match.group(5) or "IEC-UNKNOWN",
                    rule_name="IEC Checker finding",
                    severity=match.group(3).lower(),
                    description=match.group(4).strip(),
                    line_number=int(match.group(1)),
                ))
        return violations


class PlcLintTool(ExternalTool):
    """Adapter for plc-lint (lightweight ST linter).

    Expected CLI usage:
      plc-lint <file.st>

    Output format: file.st:line: severity: message
    """

    @property
    def name(self) -> str:
        return "plc-lint"

    def is_available(self) -> bool:
        return shutil.which("plc-lint") is not None

    def analyze(self, file_path: str, source_code: str | None = None) -> list[PLCRuleViolation]:
        if not self.is_available():
            return []

        tmp_file = None
        try:
            if source_code and not os.path.isfile(file_path):
                tmp_file = self._write_temp_st(source_code)
                file_path = tmp_file

            result = subprocess.run(
                ["plc-lint", file_path],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
            )

            return self._parse_output(result.stdout)

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"plc-lint failed: {e}")
            return []
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)

    def _parse_output(self, output: str) -> list[PLCRuleViolation]:
        """Parse plc-lint output."""
        violations = []
        pattern = re.compile(
            r"(?:.+?):(\d+)\s*:\s*(warning|error|info)\s*:\s*(.+)",
            re.IGNORECASE,
        )
        for line in output.split("\n"):
            match = pattern.match(line.strip())
            if match:
                violations.append(PLCRuleViolation(
                    rule_id="PLC-LINT",
                    rule_name="plc-lint finding",
                    severity=match.group(2).lower(),
                    description=match.group(3).strip(),
                    line_number=int(match.group(1)),
                ))
        return violations


class CodesysCLITool(ExternalTool):
    """Adapter for CODESYS command-line analysis.

    CODESYS Professional Development System includes a CLI for
    static analysis. This adapter calls it if available.

    Expected CLI usage:
      CODESYS.exe --analyze --project <file.project> --output json
    """

    @property
    def name(self) -> str:
        return "CODESYS CLI"

    def is_available(self) -> bool:
        # Check common CODESYS installation paths
        codesys_paths = [
            r"C:\Program Files\CODESYS 3.5.20.0\CODESYS\CODESYS.exe",
            r"C:\Program Files (x86)\CODESYS 3.5.20.0\CODESYS\CODESYS.exe",
            os.path.expandvars(r"%PROGRAMFILES%\CODESYS 3.5.20.0\CODESYS\CODESYS.exe"),
        ]
        for path in codesys_paths:
            if os.path.isfile(path):
                return True
        # Also check PATH
        return shutil.which("CODESYS") is not None

    def analyze(self, file_path: str, source_code: str | None = None) -> list[PLCRuleViolation]:
        # CODESYS CLI is complex and varies by version
        # This is a placeholder for future implementation
        logger.debug("CODESYS CLI analysis not yet implemented")
        return []


class GenericTool(ExternalTool):
    """Adapter for generic external tools that output line-based warnings.

    Configurable via constructor for any tool that outputs:
      file:line: severity: message
    or:
      file(line): severity: message
    """

    def __init__(self, tool_name: str, command: list[str]):
        self._name = tool_name
        self._command = command

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        if not self._command:
            return False
        return shutil.which(self._command[0]) is not None

    def analyze(self, file_path: str, source_code: str | None = None) -> list[PLCRuleViolation]:
        if not self.is_available():
            return []

        tmp_file = None
        try:
            if source_code and not os.path.isfile(file_path):
                tmp_file = self._write_temp_st(source_code)
                file_path = tmp_file

            cmd = [c.replace("{file}", file_path) for c in self._command]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace",
            )

            return self._parse_output(result.stdout, file_path)

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"{self._name} failed: {e}")
            return []
        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)

    def _parse_output(self, output: str, file_path: str) -> list[PLCRuleViolation]:
        """Parse generic line-based output."""
        violations = []
        patterns = [
            # file:line: severity: message
            re.compile(r"(?:.+?):(\d+)\s*:\s*(warning|error|info)\s*:\s*(.+)", re.I),
            # file(line): severity: message
            re.compile(r"(?:.+?)\((\d+)\)\s*:\s*(warning|error|info)\s*:\s*(.+)", re.I),
            # severity: line N: message
            re.compile(r"(warning|error|info)\s*:\s*line\s+(\d+)\s*:\s*(.+)", re.I),
        ]

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            for pattern in patterns:
                match = pattern.match(line)
                if match:
                    groups = match.groups()
                    if groups[0].isdigit():
                        line_num, severity, desc = int(groups[0]), groups[1], groups[2]
                    else:
                        severity, line_num, desc = groups[0], int(groups[1]), groups[2]

                    violations.append(PLCRuleViolation(
                        rule_id=f"EXT-{self._name.upper()}",
                        rule_name=f"{self._name} finding",
                        severity=severity.lower(),
                        description=desc.strip(),
                        line_number=line_num,
                    ))
                    break

        return violations


class ExternalAnalyzer:
    """Unified interface to run external PLC analysis tools.

    Automatically detects which tools are installed and runs all
    available tools, merging their findings.
    """

    def __init__(self, extra_tools: list[ExternalTool] | None = None):
        self._tools: list[ExternalTool] = [
            IECCheckerTool(),
            PlcLintTool(),
            CodesysCLITool(),
        ]
        if extra_tools:
            self._tools.extend(extra_tools)

    @property
    def available_tools(self) -> list[str]:
        """List names of available external tools."""
        return [t.name for t in self._tools if t.is_available()]

    def analyze(
        self,
        file_path: str,
        source_code: str | None = None,
        tools: list[str] | None = None,
    ) -> list[PLCRuleViolation]:
        """Run all available external tools and merge findings.

        Args:
            file_path: Path to the PLC file
            source_code: Source code (if file_path doesn't exist on disk)
            tools: Optional list of tool names to run (None = all available)

        Returns:
            Merged list of PLCRuleViolation from all tools
        """
        all_violations = []

        for tool in self._tools:
            if not tool.is_available():
                continue

            if tools and tool.name not in tools:
                continue

            try:
                violations = tool.analyze(file_path, source_code)
                if violations:
                    logger.info(
                        f"{tool.name} found {len(violations)} issue(s) in {file_path}"
                    )
                    all_violations.extend(violations)
            except Exception as e:
                logger.warning(f"{tool.name} analysis failed: {e}")

        # Deduplicate
        seen = set()
        unique = []
        for v in all_violations:
            key = (v.rule_id, v.line_number, v.description)
            if key not in seen:
                seen.add(key)
                unique.append(v)

        return unique

    def analyze_source(
        self,
        source_code: str,
        language: str = "structured_text",
    ) -> list[PLCRuleViolation]:
        """Analyze source code directly (writes to temp file if needed)."""
        tmp_file = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".st", prefix="plc_review_")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(source_code)
            tmp_file = tmp_path

            return self.analyze(tmp_file, source_code)

        finally:
            if tmp_file and os.path.exists(tmp_file):
                os.unlink(tmp_file)
