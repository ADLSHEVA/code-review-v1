"""Review output data models with Pydantic validation."""

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ReviewCategory(str, Enum):
    CODE_STYLE = "code_style"
    POTENTIAL_BUG = "potential_bug"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    READABILITY = "readability"
    CONVENTION = "convention"
    PERFORMANCE = "performance"


class ReviewComment(BaseModel):
    """A single review finding."""
    file_path: str
    line_start: int
    line_end: int | None = None
    severity: Severity
    category: ReviewCategory
    title: str = Field(max_length=200)
    description: str
    suggestion: str | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ReviewReport(BaseModel):
    """Complete review report for a diff/PR."""
    summary: str
    comments: list[ReviewComment] = []
    stats: dict[str, int] = {}
    reviewed_files: list[str] = []
    skipped_files: list[str] = []

    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.comments if c.severity == Severity.CRITICAL)

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.comments if c.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.comments if c.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for c in self.comments if c.severity == Severity.INFO)
