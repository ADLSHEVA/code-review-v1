"""Tests for OutputFormatter."""

import json
import pytest
from src.output.formatter import OutputFormatter
from src.output.models import ReviewComment, ReviewReport, Severity, ReviewCategory


@pytest.fixture
def sample_report():
    comments = [
        ReviewComment(
            file_path="app.py",
            line_start=10,
            severity=Severity.CRITICAL,
            category=ReviewCategory.SECURITY,
            title="SQL injection vulnerability",
            description="User input directly interpolated in SQL query",
            suggestion="Use parameterized queries",
            confidence=0.95,
        ),
        ReviewComment(
            file_path="utils.py",
            line_start=25,
            severity=Severity.WARNING,
            category=ReviewCategory.POTENTIAL_BUG,
            title="Missing null check",
            description="Variable could be None",
            confidence=0.8,
        ),
        ReviewComment(
            file_path="config.py",
            line_start=3,
            severity=Severity.INFO,
            category=ReviewCategory.CODE_STYLE,
            title="Line too long",
            description="Line exceeds 120 characters",
            confidence=0.7,
        ),
    ]
    return ReviewReport(
        summary="Found 3 issues: 1 critical, 1 warning, 1 info",
        comments=comments,
        stats={"critical": 1, "warning": 1, "info": 1},
        reviewed_files=["app.py", "utils.py", "config.py"],
        skipped_files=[],
    )


class TestFormatAsJson:
    def test_valid_json_output(self, sample_report):
        result = OutputFormatter.format_as_json(sample_report)
        data = json.loads(result)
        assert len(data["comments"]) == 3

    def test_json_contains_all_fields(self, sample_report):
        result = OutputFormatter.format_as_json(sample_report)
        data = json.loads(result)
        comment = data["comments"][0]
        assert comment["file_path"] == "app.py"
        assert comment["severity"] == "critical"
        assert comment["title"] == "SQL injection vulnerability"

    def test_json_dict_format(self, sample_report):
        result = OutputFormatter.format_as_json_dict(sample_report)
        assert isinstance(result, dict)
        assert "comments" in result


class TestFormatAsMarkdown:
    def test_contains_summary(self, sample_report):
        result = OutputFormatter.format_as_markdown(sample_report)
        assert "3 issues" in result or "critical" in result

    def test_contains_file_references(self, sample_report):
        result = OutputFormatter.format_as_markdown(sample_report)
        assert "app.py" in result
        assert "utils.py" in result

    def test_contains_severity_sections(self, sample_report):
        result = OutputFormatter.format_as_markdown(sample_report)
        assert "CRITICAL" in result
        assert "WARNING" in result

    def test_contains_suggestion(self, sample_report):
        result = OutputFormatter.format_as_markdown(sample_report)
        assert "parameterized queries" in result

    def test_empty_report(self):
        report = ReviewReport(summary="No issues", comments=[])
        result = OutputFormatter.format_as_markdown(report)
        assert "No issues" in result


class TestFormatAsInlineComments:
    def test_github_format(self, sample_report):
        result = OutputFormatter.format_as_inline_comments(sample_report)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_contains_path_and_line(self, sample_report):
        result = OutputFormatter.format_as_inline_comments(sample_report)
        comment = result[0]
        assert comment["path"] == "app.py"
        assert comment["line"] == 10

    def test_contains_body(self, sample_report):
        result = OutputFormatter.format_as_inline_comments(sample_report)
        assert "SQL injection" in result[0]["body"]


class TestFormatAsGithubPrReview:
    def test_critical_triggers_request_changes(self, sample_report):
        result = OutputFormatter.format_as_github_pr_review(sample_report)
        assert result["event"] == "REQUEST_CHANGES"

    def test_no_critical_approves(self):
        report = ReviewReport(
            summary="Minor issues",
            comments=[
                ReviewComment(
                    file_path="app.py",
                    line_start=1,
                    severity=Severity.INFO,
                    category=ReviewCategory.CODE_STYLE,
                    title="Style issue",
                    description="Minor style",
                    confidence=0.8,
                ),
            ],
        )
        result = OutputFormatter.format_as_github_pr_review(report)
        assert result["event"] == "COMMENT"

    def test_contains_body(self, sample_report):
        result = OutputFormatter.format_as_github_pr_review(sample_report)
        assert "body" in result
