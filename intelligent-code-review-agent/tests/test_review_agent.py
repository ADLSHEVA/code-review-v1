"""Tests for the review agent (mocked LLM calls)."""

import json
import pytest
from unittest.mock import MagicMock, patch

from src.agent.review_agent import CodeReviewAgent
from src.output.models import ReviewComment, ReviewReport, Severity, ReviewCategory


SAMPLE_LLM_RESPONSE = json.dumps([
    {
        "file_path": "test.py",
        "line_start": 5,
        "line_end": None,
        "severity": "warning",
        "category": "potential_bug",
        "title": "Missing null check",
        "description": "The variable 'user' could be None before accessing .name",
        "suggestion": "Add: if user is None: return",
        "confidence": 0.85,
    }
])


class TestCodeReviewAgent:
    @pytest.fixture
    def agent(self):
        with patch("src.agent.review_agent.ChatAnthropic"):
            agent = CodeReviewAgent(model="test-model")
            return agent

    def test_extract_json_from_code_block(self, agent):
        text = 'Here are the findings:\n```json\n[{"test": 1}]\n```'
        result = agent._extract_json(text)
        assert result == '[{"test": 1}]'

    def test_extract_json_raw(self, agent):
        text = 'Some text [{"test": 1}] more text'
        result = agent._extract_json(text)
        assert result == '[{"test": 1}]'

    def test_extract_json_none(self, agent):
        text = 'No JSON here'
        result = agent._extract_json(text)
        assert result is None

    def test_parse_valid_response(self, agent):
        from src.parsing.ast_extractor import CodeContext
        ctx = CodeContext(
            file_path="test.py", language="python",
            changed_lines=(5, 5),
        )
        comments = agent._parse_response(SAMPLE_LLM_RESPONSE, ctx)
        assert len(comments) == 1
        assert comments[0].title == "Missing null check"

    def test_parse_empty_array(self, agent):
        from src.parsing.ast_extractor import CodeContext
        ctx = CodeContext(
            file_path="test.py", language="python",
            changed_lines=(1, 1),
        )
        comments = agent._parse_response("[]", ctx)
        assert len(comments) == 0

    def test_filter_deduplication(self, agent):
        comments = [
            ReviewComment(
                file_path="a.py", line_start=1,
                severity=Severity.WARNING, category=ReviewCategory.CODE_STYLE,
                title="Same issue", description="desc",
            ),
            ReviewComment(
                file_path="a.py", line_start=1,
                severity=Severity.WARNING, category=ReviewCategory.CODE_STYLE,
                title="Same issue", description="desc duplicate",
            ),
        ]
        filtered = agent._filter_comments(comments)
        assert len(filtered) == 1

    def test_filter_by_confidence(self, agent):
        from src.parsing.ast_extractor import CodeContext
        low_confidence = json.dumps([{
            "file_path": "test.py",
            "line_start": 1,
            "severity": "info",
            "category": "code_style",
            "title": "Low confidence",
            "description": "Not sure",
            "confidence": 0.3,
        }])
        ctx = CodeContext(
            file_path="test.py", language="python",
            changed_lines=(1, 1),
        )
        comments = agent._parse_response(low_confidence, ctx)
        assert len(comments) == 0  # Filtered out by confidence threshold

    def test_compute_stats(self, agent):
        comments = [
            ReviewComment(
                file_path="a.py", line_start=1,
                severity=Severity.CRITICAL, category=ReviewCategory.SECURITY,
                title="Critical", description="desc",
            ),
            ReviewComment(
                file_path="b.py", line_start=2,
                severity=Severity.WARNING, category=ReviewCategory.CODE_STYLE,
                title="Warning", description="desc",
            ),
        ]
        stats = agent._compute_stats(comments)
        assert stats["critical"] == 1
        assert stats["warning"] == 1

    def test_generate_summary(self, agent):
        comments = [
            ReviewComment(
                file_path="a.py", line_start=1,
                severity=Severity.CRITICAL, category=ReviewCategory.SECURITY,
                title="Critical", description="desc",
            ),
        ]
        summary = agent._generate_summary(comments)
        assert "critical" in summary.lower() or "1" in summary
