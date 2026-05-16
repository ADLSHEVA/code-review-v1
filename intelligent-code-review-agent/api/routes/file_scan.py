"""Single file scan API route."""

import os
import uuid
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..models import FileScanResponse
from .scan import _reports

logger = logging.getLogger(__name__)
router = APIRouter()

# Max file size: 1 MB
MAX_FILE_SIZE = 1 * 1024 * 1024


@router.post("", response_model=FileScanResponse)
async def scan_file(file: UploadFile = File(...)):
    """Upload a single code file and scan it for vulnerabilities."""
    import sys

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from src.config import settings
    from src.agent.review_agent import CodeReviewAgent
    from src.plc.file_support import (
        extract_structured_text,
        has_plc_project_extension,
        is_plc_project_file,
    )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 1 MB)")

    # Detect language
    filename = file.filename or "unknown"
    _, ext = os.path.splitext(filename)
    language = None
    scan_source = None

    if has_plc_project_extension(filename):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            if is_plc_project_file(tmp_path):
                extracted = extract_structured_text(tmp_path)
                if extracted:
                    language = "structured_text"
                    scan_source = extracted
                elif ext.lower() == ".xml":
                    language = "structured_text"
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    if language is None:
        language = settings.language_map.get(ext.lower())

    if scan_source is None:
        try:
            scan_source = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 text")

    if not language:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {ext}. Supported: {', '.join(sorted(set(settings.language_map.values())))}",
        )

    # Run review
    try:
        agent = CodeReviewAgent()
        comments = agent.review_file_diff(filename, scan_source, scan_source)
    except Exception as e:
        logger.exception(f"File scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

    # Build report dict compatible with the report viewer
    report_id = str(uuid.uuid4())[:8]
    stats = {"critical": 0, "error": 0, "warning": 0, "info": 0}
    comment_dicts = []
    for c in comments:
        d = {
            "file_path": c.file_path,
            "line_start": c.line_start,
            "line_end": c.line_end,
            "severity": c.severity.value if hasattr(c.severity, "value") else str(c.severity),
            "category": c.category.value if hasattr(c.category, "value") else str(c.category),
            "title": c.title,
            "description": c.description,
            "suggestion": c.suggestion,
            "confidence": c.confidence,
        }
        sev = d["severity"]
        if sev in stats:
            stats[sev] += 1
        comment_dicts.append(d)

    report_dict = {
        "report_id": report_id,
        "scan_id": f"file-scan-{report_id}",
        "repo_path": filename,
        "created_at": datetime.now().isoformat(),
        "summary": f"File scan of {filename} ({language}): {len(comments)} issues found",
        "comments": comment_dicts,
        "stats": stats,
        "reviewed_files": [filename],
        "skipped_files": [],
    }
    _reports[report_id] = report_dict

    return FileScanResponse(
        report_id=report_id,
        filename=filename,
        language=language,
        issues_count=len(comments),
    )
