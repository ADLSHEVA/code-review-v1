"""Extract and parse IEC 61131-3 Structured Text code."""

import re
from dataclasses import dataclass, field

from pydantic import BaseModel


class STVariable(BaseModel):
    """A Structured Text variable declaration."""
    name: str
    data_type: str
    scope: str  # VAR, VAR_INPUT, VAR_OUTPUT, VAR_IN_OUT, VAR_GLOBAL
    initial_value: str | None = None
    comment: str | None = None


class STFunctionBlock(BaseModel):
    """A Structured Text function block or function."""
    name: str
    block_type: str  # FUNCTION_BLOCK, FUNCTION, PROGRAM
    return_type: str | None = None
    variables: list[STVariable] = []
    body: str = ""
    line_start: int = 0
    line_end: int = 0


class StructuredTextExtractor:
    """Extract and parse IEC 61131-3 Structured Text code."""

    # Regex patterns for ST constructs
    VAR_BLOCK_PATTERN = re.compile(
        r"(VAR(?:_INPUT|_OUTPUT|_IN_OUT|_GLOBAL)?)\s*(?::\s*(.+?))?\s*\n(.*?)END_VAR",
        re.DOTALL | re.IGNORECASE,
    )

    VAR_DECL_PATTERN = re.compile(
        r"(\w+)\s*:\s*(\w+(?:\s*\([^)]*\))?)(?:\s*:=\s*(.+?))?;",
        re.IGNORECASE,
    )

    FUNCTION_BLOCK_PATTERN = re.compile(
        r"(FUNCTION_BLOCK|FUNCTION|PROGRAM)\s+(\w+)(?:\s*:\s*(\w+))?",
        re.IGNORECASE,
    )

    @classmethod
    def extract_blocks(cls, source_code: str) -> list[STFunctionBlock]:
        """Extract function blocks from ST source code."""
        blocks = []
        lines = source_code.split("\n")

        current_block = None
        block_start = 0
        brace_depth = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check for block start
            match = cls.FUNCTION_BLOCK_PATTERN.match(stripped)
            if match:
                if current_block is not None:
                    current_block.line_end = i - 1
                    blocks.append(current_block)

                block_type = match.group(1)
                name = match.group(2)
                return_type = match.group(3)

                current_block = STFunctionBlock(
                    name=name,
                    block_type=block_type,
                    return_type=return_type,
                    line_start=i,
                )
                block_start = i
                continue

            # Check for block end
            if stripped.upper().startswith("END_") and current_block is not None:
                block_keyword = stripped.upper()
                if block_keyword == f"END_{current_block.block_type.upper()}":
                    current_block.line_end = i
                    blocks.append(current_block)
                    current_block = None
                    continue

            # Accumulate body
            if current_block is not None:
                current_block.body += line + "\n"

        # Close last block if needed
        if current_block is not None:
            current_block.line_end = len(lines) - 1
            blocks.append(current_block)

        return blocks

    @classmethod
    def extract_variables(cls, source_code: str) -> list[STVariable]:
        """Extract variable declarations from ST source code."""
        variables = []

        for var_block_match in cls.VAR_BLOCK_PATTERN.finditer(source_code):
            scope = var_block_match.group(1).upper()
            block_content = var_block_match.group(3)

            for var_match in cls.VAR_DECL_PATTERN.finditer(block_content):
                name = var_match.group(1)
                data_type = var_match.group(2)
                initial_value = var_match.group(3)

                variables.append(STVariable(
                    name=name,
                    data_type=data_type.strip(),
                    scope=scope,
                    initial_value=initial_value.strip() if initial_value else None,
                ))

        return variables

    @classmethod
    def extract_changed_region(
        cls, source_code: str, start_line: int, end_line: int
    ) -> str | None:
        """Extract the enclosing block for a changed line range."""
        blocks = cls.extract_blocks(source_code)

        for block in blocks:
            if block.line_start <= start_line <= block.line_end:
                return block.body

        return None
