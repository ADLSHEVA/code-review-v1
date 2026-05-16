"""Tests for the AST extractor module."""

import pytest
from src.parsing.ast_extractor import ASTExtractor, CodeContext
from src.parsing.language_support import LanguageSupport


SAMPLE_PYTHON = """\
import os
import sys
from pathlib import Path

class UserManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.users = []

    def add_user(self, name: str, email: str) -> bool:
        if not name or not email:
            return False
        user = {"name": name, "email": email}
        self.users.append(user)
        return True

    def find_user(self, name: str) -> dict | None:
        for user in self.users:
            if user["name"] == name:
                return user
        return None

def helper_function():
    return 42
"""


class TestASTExtractor:
    @pytest.fixture
    def extractor(self):
        return ASTExtractor()

    @pytest.fixture
    def lang_support(self):
        return LanguageSupport()

    def test_python_support(self, lang_support):
        assert lang_support.is_supported("python")

    def test_extract_function_context(self, extractor):
        # Line 11 is inside add_user method (1-indexed)
        ctx = extractor.extract_context(
            SAMPLE_PYTHON, "python", (11, 13), "test.py"
        )
        assert ctx.enclosing_function is not None
        assert "add_user" in ctx.enclosing_function
        assert ctx.function_name == "add_user"

    def test_extract_class_context(self, extractor):
        # Line 11 is inside UserManager class
        ctx = extractor.extract_context(
            SAMPLE_PYTHON, "python", (11, 13), "test.py"
        )
        assert ctx.enclosing_class is not None
        assert "UserManager" in ctx.enclosing_class
        assert ctx.class_name == "UserManager"

    def test_extract_imports(self, extractor):
        ctx = extractor.extract_context(
            SAMPLE_PYTHON, "python", (12, 12), "test.py"
        )
        assert len(ctx.imports) >= 2
        assert any("os" in imp for imp in ctx.imports)
        assert any("sys" in imp for imp in ctx.imports)

    def test_extract_outside_class(self, extractor):
        # Line 23-24 is helper_function, outside the class
        ctx = extractor.extract_context(
            SAMPLE_PYTHON, "python", (23, 24), "test.py"
        )
        assert ctx.enclosing_function is not None
        assert "helper_function" in ctx.enclosing_function
        assert ctx.class_name is None

    def test_unsupported_language(self, extractor):
        ctx = extractor.extract_context(
            "some code", "unknown_lang", (1, 1), "test.xyz"
        )
        assert ctx.enclosing_function is None
        assert ctx.enclosing_class is None

    def test_empty_source(self, extractor):
        ctx = extractor.extract_context("", "python", (1, 1), "empty.py")
        assert ctx.enclosing_function is None

    def test_related_symbols(self, extractor):
        ctx = extractor.extract_context(
            SAMPLE_PYTHON, "python", (9, 12), "test.py"
        )
        # Should capture symbols from the changed region
        assert isinstance(ctx.related_symbols, list)
