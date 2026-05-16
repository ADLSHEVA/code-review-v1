"""Report API routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from ..models import ReportModel, CompareRequest, CompareResult, CommentModel
from .scan import get_report, _reports

router = APIRouter()


@router.get("/{report_id}")
def get_report_detail(report_id: str):
    """Get full report details."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/comments")
def get_report_comments(
    report_id: str,
    severity: str | None = None,
    category: str | None = None,
    file_path: str | None = None,
):
    """Get filtered comments from a report."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    comments = report.get("comments", [])

    if severity:
        comments = [c for c in comments if c["severity"] == severity]
    if category:
        comments = [c for c in comments if c["category"] == category]
    if file_path:
        comments = [c for c in comments if file_path in c["file_path"]]

    return comments


@router.get("/{report_id}/files")
def get_report_files(report_id: str):
    """Get list of files in the report with issue counts."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    files = {}
    for c in report.get("comments", []):
        fp = c["file_path"]
        if fp not in files:
            files[fp] = {"file_path": fp, "total": 0, "critical": 0, "error": 0, "warning": 0, "info": 0}
        files[fp]["total"] += 1
        files[fp][c["severity"]] += 1

    return sorted(files.values(), key=lambda f: (-f["critical"], -f["error"], f["file_path"]))


@router.post("/compare")
def compare_reports(request: CompareRequest):
    """Compare two reports to find new/resolved/persistent issues."""
    report_a = get_report(request.report_id_a)
    report_b = get_report(request.report_id_b)

    if not report_a:
        raise HTTPException(status_code=404, detail=f"Report {request.report_id_a} not found")
    if not report_b:
        raise HTTPException(status_code=404, detail=f"Report {request.report_id_b} not found")

    # Build issue keys: (file, line, title)
    def issue_key(c):
        return (c["file_path"], c["line_start"], c["title"])

    keys_a = {issue_key(c): c for c in report_a.get("comments", [])}
    keys_b = {issue_key(c): c for c in report_b.get("comments", [])}

    new_issues = [c for k, c in keys_b.items() if k not in keys_a]
    resolved_issues = [c for k, c in keys_a.items() if k not in keys_b]
    persistent_issues = [c for k, c in keys_b.items() if k in keys_a]

    return {
        "report_a": report_a,
        "report_b": report_b,
        "new_issues": new_issues,
        "resolved_issues": resolved_issues,
        "persistent_issues": persistent_issues,
        "summary": {
            "new_count": len(new_issues),
            "resolved_count": len(resolved_issues),
            "persistent_count": len(persistent_issues),
        },
    }
