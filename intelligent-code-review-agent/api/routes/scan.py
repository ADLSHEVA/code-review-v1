"""Scan API routes."""

import uuid
import logging
import threading
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks

from ..models import ScanRequest, ScanJob, ScanStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job store (replace with DB in production)
_jobs: dict[str, ScanJob] = {}
_reports: dict[str, dict] = {}


def _detect_default_branch(repo_path: str) -> str:
    """Detect the default branch of a git repository."""
    import git
    try:
        repo = git.Repo(repo_path)
        # Try origin/HEAD first
        try:
            ref = repo.git.symbolic_ref("refs/remotes/origin/HEAD")
            return ref.replace("refs/remotes/origin/", "")
        except Exception:
            pass
        # Try common branch names
        for name in ["main", "master", "develop", "dev"]:
            if name in [h.name for h in repo.heads]:
                return name
        # Fallback to active branch
        return repo.active_branch.name
    except Exception:
        return "main"


def _ensure_git_repo(repo_path: str) -> str:
    """Ensure the path is a git repo. If not, init + commit. Returns commit SHA."""
    import git
    from pathlib import Path

    # Check if already a git repo
    try:
        repo = git.Repo(repo_path)
        repo.git.status()
        return ""  # Already a valid git repo, no special handling needed
    except Exception:
        pass

    # Not a git repo — initialize one
    logger.info(f"No git repo found at {repo_path}, auto-initializing...")
    repo = git.Repo.init(repo_path)

    # Write a .gitignore for common non-source dirs
    gitignore = Path(repo_path) / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "node_modules/\n__pycache__/\n.git/\nvenv/\n.venv/\n"
            "dist/\nbuild/\n*.pyc\n*.pyo\n.idea/\n.vscode/\n",
            encoding="utf-8",
        )

    repo.git.add(A=True)
    repo.index.commit("Initial commit for code review scan")
    return repo.head.commit.hexsha


def _run_scan(job_id: str, request: ScanRequest):
    """Run the actual scan in a background thread."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    job = _jobs[job_id]
    job.status = ScanStatus.RUNNING
    job.started_at = datetime.now().isoformat()

    try:
        logger.info(f"[{job_id}] Starting scan for: {request.repo_path}")

        from src.config import settings
        from src.git.repo_manager import RepoManager
        from src.agent.review_agent import CodeReviewAgent
        from src.output.formatter import OutputFormatter
        from src.git.models import DiffResult

        # Ensure git repo exists (auto-init if needed)
        auto_commit = _ensure_git_repo(request.repo_path)
        logger.info(f"[{job_id}] ensure_git_repo returned: '{auto_commit}'")

        # Get diff
        logger.info(f"[{job_id}] Getting diff, auto_commit='{auto_commit}', commit_sha={request.commit_sha}")
        if auto_commit:
            # Repo was auto-initialized — scan the initial commit
            diff_result = RepoManager.get_diff_from_commit(
                request.repo_path, auto_commit
            )
        elif request.commit_sha:
            diff_result = RepoManager.get_diff_from_commit(
                request.repo_path, request.commit_sha
            )
        else:
            base = request.base_ref
            if not base:
                base = _detect_default_branch(request.repo_path)
            diff_result = RepoManager.get_diff(
                request.repo_path,
                base,
                request.head_ref or "HEAD",
            )

        # Apply file filter
        if request.files_filter:
            filtered_files = [
                f for f in diff_result.files
                if any(fp in f.file_path for fp in request.files_filter)
            ]
            diff_result = DiffResult(
                commit_sha=diff_result.commit_sha,
                base_ref=diff_result.base_ref,
                head_ref=diff_result.head_ref,
                files=filtered_files,
            )

        job.total_files = len(diff_result.files)

        # Run review
        def on_progress(file_path: str, current: int, total: int):
            job.current_file = file_path
            job.progress = int(((current + 1) / total) * 100) if total > 0 else 0

        agent = CodeReviewAgent(model=request.model)
        report = agent.review_diff(diff_result, request.repo_path, progress_callback=on_progress)

        # Store report
        report_id = str(uuid.uuid4())[:8]
        from src.output.formatter import OutputFormatter
        report_dict = OutputFormatter.format_as_json_dict(report)
        report_dict["report_id"] = report_id
        report_dict["scan_id"] = job_id
        report_dict["repo_path"] = request.repo_path
        report_dict["created_at"] = datetime.now().isoformat()
        _reports[report_id] = report_dict

        # Save markdown report too
        md_content = OutputFormatter.format_as_markdown(report)
        report_path = Path(request.repo_path) / f"audit_report_{report_id}.md"
        report_path.write_text(md_content, encoding="utf-8")

        job.status = ScanStatus.COMPLETED
        job.completed_at = datetime.now().isoformat()
        job.progress = 100
        job.report_id = report_id

    except Exception as e:
        logger.exception(f"Scan failed: {e}")
        job.status = ScanStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.now().isoformat()


@router.post("/start", response_model=ScanJob)
def start_scan(request: ScanRequest):
    """Start a new code review scan."""
    from pathlib import Path

    repo_path = Path(request.repo_path)

    # Validate path exists
    if not repo_path.exists():
        job_id = str(uuid.uuid4())[:8]
        job = ScanJob(
            job_id=job_id,
            status=ScanStatus.FAILED,
            repo_path=request.repo_path,
            created_at=datetime.now().isoformat(),
            error=f"Path does not exist: {request.repo_path}",
        )
        _jobs[job_id] = job
        return job

    # Auto-correct: if user points at node_modules or similar, go up to parent
    skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"}
    if repo_path.name in skip_dirs:
        parent = repo_path.parent
        logger.info(f"Path is {repo_path.name}/, redirecting to parent: {parent}")
        repo_path = parent
        request.repo_path = str(parent)
        logger.info(f"Corrected repo_path to: {request.repo_path}")

    job_id = str(uuid.uuid4())[:8]
    logger.info(f"Creating scan job {job_id} for path: {request.repo_path}")
    job = ScanJob(
        job_id=job_id,
        status=ScanStatus.PENDING,
        repo_path=request.repo_path,
        created_at=datetime.now().isoformat(),
    )
    _jobs[job_id] = job

    thread = threading.Thread(target=_run_scan, args=(job_id, request), daemon=True)
    thread.start()

    return job


@router.get("/status/{job_id}", response_model=ScanJob)
def get_scan_status(job_id: str):
    """Get the status of a scan job."""
    if job_id not in _jobs:
        return {"error": "Job not found"}
    return _jobs[job_id]


@router.get("/jobs", response_model=list[ScanJob])
def list_jobs():
    """List all scan jobs."""
    return sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)


@router.get("/reports")
def list_reports():
    """List all available reports."""
    return [
        {
            "report_id": r["report_id"],
            "scan_id": r["scan_id"],
            "repo_path": r["repo_path"],
            "created_at": r["created_at"],
            "total_comments": len(r.get("comments", [])),
        }
        for r in _reports.values()
    ]


def get_report(report_id: str) -> dict | None:
    """Get a report by ID (used by report routes)."""
    return _reports.get(report_id)
