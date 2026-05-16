"""Tests for the output models."""

import pytest
from pydantic import ValidationError
from src.output.models import (
    Severity, ReviewCategory, ReviewComment, ReviewReport
)


class TestReviewComment:
    def test_valid_comment(self):
        comment = ReviewComment(
            file_path="test.py",
            line_start=10,
            severity=Severity.WARNING,
            category=ReviewCategory.POTENTIAL_BUG,
            title="Missing null check",
            description="The variable could be None.",
        )
        assert comment.file_path == "test.py"
        assert comment.confidence == 0.8  # default

    def test_comment_with_suggestion(self):
        comment = ReviewComment(
            file_path="test.py",
            line_start=5,
            line_end=10,
            severity=Severity.ERROR,
            category=ReviewCategory.SECURITY,
            title="SQL injection",
            description="User input used in SQL query.",
            suggestion="Use parameterized queries.",
            confidence=0.95,
        )
        assert comment.suggestion == "Use parameterized queries."

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            ReviewComment(
                file_path="test.py",
                line_start=1,
                severity="invalid",
                category=ReviewCategory.CODE_STYLE,
                title="Test",
                description="Test",
            )

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ReviewComment(
                file_path="test.py",
                line_start=1,
                severity=Severity.INFO,
                category=ReviewCategory.CODE_STYLE,
                title="Test",
                description="Test",
                confidence=1.5,  # Out of range
            )


class TestReviewReport:
    def test_empty_report(self):
        report = ReviewReport(summary="No issues found.")
        assert report.critical_count == 0
        assert report.error_count == 0
        assert len(report.comments) == 0

    def test_report_with_comments(self):
        comments = [
            ReviewComment(
                file_path="a.py", line_start=1,
                severity=Severity.CRITICAL, category=ReviewCategory.SECURITY,
                title="Critical", description="desc",
            ),
            ReviewComment(
                file_path="b.py", line_start=5,
                severity=Severity.WARNING, category=ReviewCategory.CODE_STYLE,
                title="Warning", description="desc",
            ),
        ]
        report = ReviewReport(
            summary="Found 2 issues",
            comments=comments,
            stats={"critical": 1, "warning": 1},
            reviewed_files=["a.py", "b.py"],
        )
        assert report.critical_count == 1
        assert report.warning_count == 1
        assert len(report.reviewed_files) == 2
