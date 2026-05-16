"""Tests for ContextBuilder and CodeContext."""

import os
import tempfile
import pytest
from src.parsing.ast_extractor import CodeContext, ASTExtractor
from src.parsing.context_builder import ContextBuilder


class TestCodeContext:
    """Tests for CodeContext model."""

    def test_basic_fields(self):
        ctx = CodeContext(
            file_path="app.py",
            language="python",
            changed_lines=(10, 15),
        )
        assert ctx.file_path == "app.py"
        assert ctx.language == "python"
        assert ctx.changed_lines == (10, 15)

    def test_optional_fields_default_none(self):
        ctx = CodeContext(file_path="app.py", language="python", changed_lines=(1, 1))
        assert ctx.enclosing_function is None
        assert ctx.enclosing_class is None
        assert ctx.function_name is None
        assert ctx.class_name is None
        assert ctx.full_source is None
        assert ctx.diff_text is None

    def test_full_source_field(self):
        """full_source should be a declared field, not dynamic."""
        ctx = CodeContext(
            file_path="app.py",
            language="python",
            changed_lines=(1, 5),
            full_source="def hello():\n    pass\n",
        )
        assert ctx.full_source == "def hello():\n    pass\n"

    def test_diff_text_field(self):
        """diff_text should be a declared field, not dynamic."""
        ctx = CodeContext(
            file_path="app.py",
            language="python",
            changed_lines=(1, 5),
            diff_text="+def hello():\n+    pass\n",
        )
        assert ctx.diff_text == "+def hello():\n+    pass\n"

    def test_model_copy_with_full_source(self):
        """model_copy should work with the declared full_source field."""
        ctx = CodeContext(file_path="app.py", language="python", changed_lines=(1, 1))
        updated = ctx.model_copy(update={"full_source": "new source"})
        assert updated.full_source == "new source"
        assert updated.file_path == "app.py"

    def test_model_copy_with_diff_text(self):
        ctx = CodeContext(file_path="app.py", language="python", changed_lines=(1, 1))
        updated = ctx.model_copy(update={"diff_text": "+new line"})
        assert updated.diff_text == "+new line"

    def test_imports_and_symbols_default_empty(self):
        ctx = CodeContext(file_path="app.py", language="python", changed_lines=(1, 1))
        assert ctx.imports == []
        assert ctx.related_symbols == []


class TestASTExtractor:
    """Tests for ASTExtractor."""

    def test_python_function_extraction(self, sample_python_file):
        extractor = ASTExtractor()
        # Find the 'add' method — use line with 'result = a + b'
        lines = sample_python_file.split("\n")
        target_line = next(i + 1 for i, l in enumerate(lines) if "result = a + b" in l)
        ctx = extractor.extract_context(
            sample_python_file, "python", (target_line, target_line), "calculator.py"
        )
        assert ctx.function_name == "add"
        assert ctx.class_name == "Calculator"
        assert ctx.enclosing_function is not None
        assert ctx.enclosing_class is not None

    def test_python_top_level_function(self, sample_python_file):
        extractor = ASTExtractor()
        lines = sample_python_file.split("\n")
        target_line = next(i + 1 for i, l in enumerate(lines) if "return Path.cwd()" in l)
        ctx = extractor.extract_context(
            sample_python_file, "python", (target_line, target_line), "calculator.py"
        )
        assert ctx.function_name == "utility"
        assert ctx.class_name is None

    def test_python_imports(self, sample_python_file):
        extractor = ASTExtractor()
        ctx = extractor.extract_context(
            sample_python_file, "python", (1, 1), "calculator.py"
        )
        assert len(ctx.imports) >= 2
        assert any("os" in imp for imp in ctx.imports)
        assert any("Path" in imp for imp in ctx.imports)

    def test_unsupported_language_returns_empty_context(self):
        extractor = ASTExtractor()
        ctx = extractor.extract_context(
            "some code", "brainfuck", (1, 1), "test.bf"
        )
        assert ctx.enclosing_function is None
        assert ctx.enclosing_class is None

    def test_javascript_function(self):
        extractor = ASTExtractor()
        js_code = """
function greet(name) {
    return "Hello, " + name;
}

class App {
    render() {
        return "<div/>";
    }
}
"""
        ctx = extractor.extract_context(js_code, "javascript", (3, 3), "app.js")
        assert ctx.function_name == "greet"

    def test_related_symbols(self, sample_python_file):
        extractor = ASTExtractor()
        lines = sample_python_file.split("\n")
        target_line = next(i + 1 for i, l in enumerate(lines) if "result = a + b" in l)
        ctx = extractor.extract_context(
            sample_python_file, "python", (target_line, target_line), "calculator.py"
        )
        # Should find symbols like 'result', 'a', 'b', 'history'
        assert len(ctx.related_symbols) > 0


class TestContextBuilder:
    """Tests for ContextBuilder."""

    def test_build_context_from_file(self, temp_repo_dir):
        # Create a test file
        test_file = os.path.join(temp_repo_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    return 'world'\n")

        builder = ContextBuilder()
        from src.git.models import ChangedFile, DiffHunk, DiffLine, ChangeType

        changed = ChangedFile(
            file_path="test.py",
            change_type=ChangeType.ADDED,
            language="python",
            hunks=[
                DiffHunk(
                    old_start=0, old_count=0, new_start=1, new_count=2,
                    lines=[
                        DiffLine(content="def hello():", line_type="+", new_line=1),
                        DiffLine(content="    return 'world'", line_type="+", new_line=2),
                    ],
                )
            ],
        )

        from src.git.models import DiffResult
        diff_result = DiffResult(
            commit_sha="abc123",
            base_ref=None,
            head_ref="abc123",
            files=[changed],
        )

        contexts = builder.build_review_context(diff_result, temp_repo_dir)
        assert len(contexts) == 1
        ctx = contexts[0]
        assert ctx.full_source is not None
        assert "def hello" in ctx.full_source
        assert ctx.diff_text is not None
