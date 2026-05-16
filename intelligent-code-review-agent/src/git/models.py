"""Data models for git diff representation."""

from enum import Enum
from pydantic import BaseModel


class ChangeType(str, Enum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    RENAMED = "renamed"


class DiffLine(BaseModel):
    line_number_old: int | None = None
    line_number_new: int | None = None
    content: str
    is_added: bool = False
    is_deleted: bool = False


class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine] = []

    @property
    def added_lines(self) -> list[DiffLine]:
        return [line for line in self.lines if line.is_added]

    @property
    def deleted_lines(self) -> list[DiffLine]:
        return [line for line in self.lines if line.is_deleted]

    @property
    def changed_range_new(self) -> tuple[int, int]:
        """Return (start, end) line numbers in the new file."""
        added = [l for l in self.lines if l.is_added or (not l.is_deleted and l.line_number_new)]
        if not added:
            return (self.new_start, self.new_start + self.new_count)
        nums = [l.line_number_new for l in added if l.line_number_new is not None]
        if nums:
            return (min(nums), max(nums))
        return (self.new_start, self.new_start + self.new_count)


class ChangedFile(BaseModel):
    file_path: str
    change_type: ChangeType = ChangeType.MODIFIED
    language: str | None = None
    hunks: list[DiffHunk] = []
    old_content: str | None = None
    new_content: str | None = None

    @property
    def added_lines_count(self) -> int:
        return sum(len(h.added_lines) for h in self.hunks)

    @property
    def deleted_lines_count(self) -> int:
        return sum(len(h.deleted_lines) for h in self.hunks)


class DiffResult(BaseModel):
    """Complete parsed diff for one commit or PR."""
    commit_sha: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    files: list[ChangedFile] = []

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_added(self) -> int:
        return sum(f.added_lines_count for f in self.files)

    @property
    def total_deleted(self) -> int:
        return sum(f.deleted_lines_count for f in self.files)
