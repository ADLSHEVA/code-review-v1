"""Tests for SeverityClassifier."""

import pytest
from src.output.severity import SeverityClassifier
from src.output.models import Severity, ReviewCategory


class TestClassify:
    """Tests for SeverityClassifier.classify()."""

    def test_critical_sql_injection(self):
        result = SeverityClassifier.classify(
            ReviewCategory.SECURITY, "SQL injection vulnerability in query builder"
        )
        assert result == Severity.CRITICAL

    def test_critical_rce(self):
        result = SeverityClassifier.classify(
            ReviewCategory.SECURITY, "Remote code execution via eval()"
        )
        assert result == Severity.CRITICAL

    def test_critical_hardcoded_secret(self):
        result = SeverityClassifier.classify(
            ReviewCategory.SECURITY, "Hardcoded API key found in config"
        )
        assert result == Severity.CRITICAL

    def test_critical_xss(self):
        result = SeverityClassifier.classify(
            ReviewCategory.SECURITY, "XSS vulnerability in user input rendering"
        )
        assert result == Severity.CRITICAL

    def test_error_null_pointer(self):
        result = SeverityClassifier.classify(
            ReviewCategory.POTENTIAL_BUG, "Null pointer dereference possible"
        )
        assert result == Severity.ERROR

    def test_error_resource_leak(self):
        result = SeverityClassifier.classify(
            ReviewCategory.POTENTIAL_BUG, "Resource leak: file handle not closed"
        )
        assert result == Severity.ERROR

    def test_rce_not_false_positive_on_resource(self):
        """'rce' keyword should not match inside 'resource'."""
        result = SeverityClassifier.classify(
            ReviewCategory.POTENTIAL_BUG, "Resource leak in connection pool"
        )
        assert result != Severity.CRITICAL

    def test_error_race_condition(self):
        result = SeverityClassifier.classify(
            ReviewCategory.POTENTIAL_BUG, "Race condition in concurrent access"
        )
        assert result == Severity.ERROR

    def test_suggested_severity_used_when_no_keyword_match(self):
        result = SeverityClassifier.classify(
            ReviewCategory.CODE_STYLE, "Variable name too short", Severity.WARNING
        )
        assert result == Severity.WARNING

    def test_category_default_fallback(self):
        result = SeverityClassifier.classify(
            ReviewCategory.CODE_STYLE, "Minor formatting issue"
        )
        assert result == Severity.INFO

    def test_category_default_security(self):
        result = SeverityClassifier.classify(
            ReviewCategory.SECURITY, "Some security consideration"
        )
        assert result == Severity.ERROR

    def test_keyword_overrides_suggested(self):
        """Keywords should escalate even if suggested severity is lower."""
        result = SeverityClassifier.classify(
            ReviewCategory.CODE_STYLE, "SQL injection in query", Severity.INFO
        )
        assert result == Severity.CRITICAL

    def test_case_insensitive_keywords(self):
        result = SeverityClassifier.classify(
            ReviewCategory.SECURITY, "SQL INJECTION vulnerability"
        )
        assert result == Severity.CRITICAL


class TestValidateSeverity:
    """Tests for SeverityClassifier.validate_severity()."""

    def test_low_confidence_downgrades_to_info(self):
        result = SeverityClassifier.validate_severity(
            Severity.CRITICAL, ReviewCategory.SECURITY, confidence=0.3
        )
        assert result == Severity.INFO

    def test_medium_confidence_downgrades_critical_to_warning(self):
        result = SeverityClassifier.validate_severity(
            Severity.CRITICAL, ReviewCategory.SECURITY, confidence=0.6
        )
        assert result == Severity.WARNING

    def test_medium_confidence_downgrades_error_to_warning(self):
        result = SeverityClassifier.validate_severity(
            Severity.ERROR, ReviewCategory.POTENTIAL_BUG, confidence=0.65
        )
        assert result == Severity.WARNING

    def test_high_confidence_preserves_critical(self):
        result = SeverityClassifier.validate_severity(
            Severity.CRITICAL, ReviewCategory.SECURITY, confidence=0.9
        )
        assert result == Severity.CRITICAL

    def test_high_confidence_preserves_error(self):
        result = SeverityClassifier.validate_severity(
            Severity.ERROR, ReviewCategory.POTENTIAL_BUG, confidence=0.8
        )
        assert result == Severity.ERROR

    def test_medium_confidence_preserves_warning(self):
        """Warning should not be downgraded by medium confidence."""
        result = SeverityClassifier.validate_severity(
            Severity.WARNING, ReviewCategory.PERFORMANCE, confidence=0.6
        )
        assert result == Severity.WARNING

    def test_boundary_confidence_05(self):
        result = SeverityClassifier.validate_severity(
            Severity.ERROR, ReviewCategory.POTENTIAL_BUG, confidence=0.5
        )
        assert result == Severity.WARNING

    def test_boundary_confidence_07(self):
        result = SeverityClassifier.validate_severity(
            Severity.CRITICAL, ReviewCategory.SECURITY, confidence=0.7
        )
        assert result == Severity.CRITICAL
