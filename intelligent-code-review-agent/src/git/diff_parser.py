"""Parse unified diff format into structured DiffHunk models."""

import re

from .models import DiffHunk, DiffLine


class DiffParser:
    """Parses unified diff text into structured data."""

    # Pattern for hunk headers: @@ -old_start,old_count +new_start,new_count @@
    HUNK_HEADER_PATTERN = re.compile(
        r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$"
    )

    @classmethod
    def parse_unified_diff(cls, diff_text: str) -> list[DiffHunk]:
        """Parse a unified diff string into a list of DiffHunk objects."""
        hunks: list[DiffHunk] = []
        current_hunk: DiffHunk | None = None
        old_line = 0
        new_line = 0

        for raw_line in diff_text.split("\n"):
            # Skip diff headers (diff --git, index, --- a/, +++ b/)
            if raw_line.startswith(("diff --git", "index ", "--- ", "+++ ")):
                continue

            match = cls.HUNK_HEADER_PATTERN.match(raw_line)
            if match:
                # Save previous hunk if exists
                if current_hunk is not None:
                    hunks.append(current_hunk)

                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1

                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    lines=[],
                )
                old_line = old_start
                new_line = new_start
                continue

            if current_hunk is None:
                continue

            if raw_line.startswith("+"):
                diff_line = DiffLine(
                    line_number_old=None,
                    line_number_new=new_line,
                    content=raw_line[1:],
                    is_added=True,
                )
                current_hunk.lines.append(diff_line)
                new_line += 1
            elif raw_line.startswith("-"):
                diff_line = DiffLine(
                    line_number_old=old_line,
                    line_number_new=None,
                    content=raw_line[1:],
                    is_deleted=True,
                )
                current_hunk.lines.append(diff_line)
                old_line += 1
            elif raw_line.startswith(" ") or raw_line == "":
                # Context line
                content = raw_line[1:] if raw_line.startswith(" ") else ""
                diff_line = DiffLine(
                    line_number_old=old_line,
                    line_number_new=new_line,
                    content=content,
                )
                current_hunk.lines.append(diff_line)
                old_line += 1
                new_line += 1
            # Lines like "\ No newline at end of file" are skipped

        # Don't forget the last hunk
        if current_hunk is not None:
            hunks.append(current_hunk)

        return hunks

    @classmethod
    def extract_changed_line_ranges(cls, hunks: list[DiffHunk]) -> list[tuple[int, int]]:
        """Extract (start, end) line ranges for changed regions in the new file."""
        ranges = []
        for hunk in hunks:
            ranges.append(hunk.changed_range_new)
        return ranges
