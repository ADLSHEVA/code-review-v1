"""API request/response models."""

from enum import Enum
from pydantic import BaseModel, Field


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanRequest(BaseModel):
    repo_path: str = Field(..., description="Path to git repository")
    commit_sha: str | None = Field(None, description="Commit SHA to review")
    base_ref: str | None = Field(None, description="Base ref for diff")
    head_ref: str | None = Field(None, description="Head ref for diff")
    model: str | None = Field(None, description="LLM model override")
    files_filter: list[str] | None = Field(None, description="Only scan these file paths")


class ScanJob(BaseModel):
    job_id: str
    status: ScanStatus
    repo_path: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    progress: int = 0
    total_files: int = 0
    current_file: str | None = None
    error: str | None = None
    report_id: str | None = None


class SeverityCount(BaseModel):
    critical: int = 0
    error: int = 0
    warning: int = 0
    info: int = 0


class CommentModel(BaseModel):
    file_path: str
    line_start: int
    line_end: int | None = None
    severity: str
    category: str
    title: str
    description: str
    suggestion: str | None = None
    confidence: float


class ReportModel(BaseModel):
    report_id: str
    scan_id: str
    repo_path: str
    created_at: str
    summary: str
    comments: list[CommentModel]
    stats: SeverityCount
    reviewed_files: list[str]
    skipped_files: list[str]


class CompareRequest(BaseModel):
    report_id_a: str
    report_id_b: str


class CompareResult(BaseModel):
    report_a: ReportModel
    report_b: ReportModel
    new_issues: list[CommentModel]
    resolved_issues: list[CommentModel]
    persistent_issues: list[CommentModel]


class ConfigModel(BaseModel):
    claude_model: str
    confidence_threshold: float
    max_context_tokens: int
    temperature: float
    log_level: str
    supported_languages: list[str]


class GuidelineFile(BaseModel):
    filename: str
    size_bytes: int
    uploaded_at: str
    doc_count: int


class GuidelineListResponse(BaseModel):
    files: list[GuidelineFile]
    total_files: int
    total_chunks: int


class GuidelineUploadResponse(BaseModel):
    filename: str
    size_bytes: int
    chunks_indexed: int
    message: str


class ReindexResponse(BaseModel):
    files_processed: int
    chunks_indexed: int
    message: str


class FileScanResponse(BaseModel):
    report_id: str
    filename: str
    language: str
    issues_count: int
