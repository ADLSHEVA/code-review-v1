"""Run a focused code audit on src/ Python files and generate a markdown report."""

import sys
import os

agent_root = os.path.dirname(os.path.abspath(__file__))
os.chdir(agent_root)
sys.path.insert(0, agent_root)

from src.config import settings
from src.git.repo_manager import RepoManager
from src.agent.review_agent import CodeReviewAgent
from src.output.formatter import OutputFormatter
from src.output.models import ReviewReport

TARGET_REPO = r"D:\AI_Models\quant-alpha-foundation"
OUTPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else r"D:\AI_Models\quant-alpha-foundation\audit_report_v1.md"

print(f"Model: {settings.claude_model}")
print(f"Target: {TARGET_REPO}")
print(f"Output: {OUTPUT_FILE}")
print()

# Get the full diff
print("Fetching diff...")
diff_result = RepoManager.get_diff_from_commit(TARGET_REPO, "HEAD")

# Filter to only src/ Python files
src_files = [f for f in diff_result.files if f.file_path.startswith("src/") and f.file_path.endswith(".py")]
print(f"Total files: {diff_result.total_files}, src/ Python files: {len(src_files)}")

# Create a filtered DiffResult
from src.git.models import DiffResult
filtered = DiffResult(
    commit_sha=diff_result.commit_sha,
    base_ref=diff_result.base_ref,
    head_ref=diff_result.head_ref,
    files=src_files,
)
print(f"Files to review: {filtered.total_files}, +{filtered.total_added} -{filtered.total_deleted} lines")

# Run the review
print("Running AI review...")
agent = CodeReviewAgent()
report = agent.review_diff(filtered, TARGET_REPO)

# Generate markdown report
md_content = OutputFormatter.format_as_markdown(report)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"\nAudit complete!")
print(f"  Total comments: {len(report.comments)}")
print(f"  Critical: {report.critical_count}")
print(f"  Errors: {report.error_count}")
print(f"  Warnings: {report.warning_count}")
print(f"  Info: {report.info_count}")
print(f"  Reviewed files: {len(report.reviewed_files)}")
print(f"  Skipped files: {len(report.skipped_files)}")
print(f"\nReport saved to: {OUTPUT_FILE}")
