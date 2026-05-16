"""Severity classification logic."""

import re
from .models import ReviewCategory, Severity


class SeverityClassifier:
    """Classifies and validates severity levels for review comments."""

    # Default severity mapping by category
    CATEGORY_SEVERITY_MAP: dict[ReviewCategory, Severity] = {
        ReviewCategory.SECURITY: Severity.ERROR,
        ReviewCategory.POTENTIAL_BUG: Severity.WARNING,
        ReviewCategory.ARCHITECTURE: Severity.WARNING,
        ReviewCategory.PERFORMANCE: Severity.WARNING,
        ReviewCategory.CODE_STYLE: Severity.INFO,
        ReviewCategory.READABILITY: Severity.INFO,
        ReviewCategory.CONVENTION: Severity.INFO,
    }

    # Keywords that escalate severity
    CRITICAL_KEYWORDS = {
        "sql injection", "remote code execution", "rce", "authentication bypass",
        "hardcoded password", "hardcoded secret", "hardcoded api key",
        "path traversal", "command injection", "xss", "csrf",
    }

    ERROR_KEYWORDS = {
        "null pointer", "none check", "missing validation", "unhandled exception",
        "resource leak", "memory leak", "race condition", "deadlock",
        "off-by-one", "infinite loop", "uncaught",
    }

    @classmethod
    def _keyword_match(cls, keyword: str, text: str) -> bool:
        """Match keyword with word boundaries to avoid false positives."""
        if len(keyword) <= 4:
            # Short keywords: use word boundary regex (e.g. "rce" shouldn't match "resource")
            return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))
        return keyword in text

    @classmethod
    def classify(
        cls,
        category: ReviewCategory,
        description: str,
        suggested_severity: Severity | None = None,
    ) -> Severity:
        """Determine the appropriate severity for a review comment."""
        desc_lower = description.lower()

        # Check for critical security issues
        if any(cls._keyword_match(kw, desc_lower) for kw in cls.CRITICAL_KEYWORDS):
            return Severity.CRITICAL

        # Check for error-level issues
        if any(cls._keyword_match(kw, desc_lower) for kw in cls.ERROR_KEYWORDS):
            return Severity.ERROR

        # Use suggested severity if provided and reasonable
        if suggested_severity is not None:
            return suggested_severity

        # Fall back to category default
        return cls.CATEGORY_SEVERITY_MAP.get(category, Severity.INFO)

    @classmethod
    def validate_severity(
        cls, severity: Severity, category: ReviewCategory, confidence: float
    ) -> Severity:
        """Validate and potentially downgrade severity based on confidence."""
        # Low confidence -> downgrade
        if confidence < 0.5:
            return Severity.INFO
        if confidence < 0.7 and severity in (Severity.CRITICAL, Severity.ERROR):
            return Severity.WARNING

        return severity
