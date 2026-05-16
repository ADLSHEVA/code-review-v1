"""Output formatting for review reports."""

import json
from io import StringIO

from .models import ReviewReport, Severity


class OutputFormatter:
    """Format ReviewReport into various output formats."""

    @staticmethod
    def format_as_json(report: ReviewReport) -> str:
        """Format report as JSON string."""
        return report.model_dump_json(indent=2)

    @staticmethod
    def format_as_json_dict(report: ReviewReport) -> dict:
        """Format report as a Python dictionary."""
        return report.model_dump()

    @classmethod
    def format_as_markdown(cls, report: ReviewReport) -> str:
        """Format report as a human-readable Markdown document."""
        buf = StringIO()

        buf.write("# Code Review Report\n\n")

        # Summary
        buf.write("## Summary\n\n")
        buf.write(f"{report.summary}\n\n")

        # Stats
        if report.stats:
            buf.write("### Statistics\n\n")
            buf.write("| Metric | Count |\n")
            buf.write("|--------|-------|\n")
            for key, value in report.stats.items():
                if not key.startswith("cat_"):
                    buf.write(f"| {key.replace('_', ' ').title()} | {value} |\n")
            buf.write("\n")

        # Files reviewed
        buf.write(f"**Files Reviewed**: {len(report.reviewed_files)}\n")
        if report.skipped_files:
            buf.write(f"**Files Skipped**: {len(report.skipped_files)}\n")
        buf.write("\n---\n\n")

        # Group comments by severity
        severity_groups = {
            Severity.CRITICAL: [],
            Severity.ERROR: [],
            Severity.WARNING: [],
            Severity.INFO: [],
        }
        for comment in report.comments:
            severity_groups[comment.severity].append(comment)

        severity_emoji = {
            Severity.CRITICAL: "CRITICAL",
            Severity.ERROR: "ERROR",
            Severity.WARNING: "WARNING",
            Severity.INFO: "INFO",
        }

        for severity, comments in severity_groups.items():
            if not comments:
                continue

            buf.write(f"## {severity_emoji[severity]} Issues ({len(comments)})\n\n")

            for i, comment in enumerate(comments, 1):
                line_info = f":{comment.line_start}"
                if comment.line_end and comment.line_end != comment.line_start:
                    line_info = f":{comment.line_start}-{comment.line_end}"

                buf.write(f"### [{severity.value.upper()}] {comment.title}\n\n")
                buf.write(f"**File**: `{comment.file_path}{line_info}`\n")
                buf.write(f"**Category**: {comment.category.value.replace('_', ' ').title()}\n")
                buf.write(f"**Confidence**: {comment.confidence:.0%}\n\n")
                buf.write(f"{comment.description}\n\n")

                if comment.suggestion:
                    buf.write(f"**Suggestion**:\n```\n{comment.suggestion}\n```\n\n")

                buf.write("---\n\n")

        if not report.comments:
            buf.write("No issues found. The code looks good! :)\n")

        return buf.getvalue()

    @classmethod
    def format_as_inline_comments(cls, report: ReviewReport) -> list[dict]:
        """Format as inline comments suitable for GitHub/GitLab API."""
        comments = []
        for comment in report.comments:
            comments.append({
                "path": comment.file_path,
                "line": comment.line_start,
                "side": "RIGHT",
                "body": (
                    f"**[{comment.severity.value.upper()}]** {comment.title}\n\n"
                    f"{comment.description}\n\n"
                    f"*Category: {comment.category.value} | "
                    f"Confidence: {comment.confidence:.0%}*\n\n"
                    + (f"**Suggestion:**\n```\n{comment.suggestion}\n```" if comment.suggestion else "")
                ),
            })
        return comments

    @classmethod
    def format_as_github_pr_review(cls, report: ReviewReport) -> dict:
        """Format as a GitHub PR review request body."""
        return {
            "body": cls.format_as_markdown(report),
            "event": "COMMENT" if not report.critical_count else "REQUEST_CHANGES",
            "comments": cls.format_as_inline_comments(report),
        }
