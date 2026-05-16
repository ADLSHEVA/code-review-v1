"""Tests for the RAG document loader."""

import os
import tempfile

import pytest
from src.rag.document_loader import DocumentLoader


SAMPLE_MARKDOWN = """\
# Python Best Practices

## Naming Conventions

Use snake_case for variables and functions.
Use PascalCase for classes.

## Error Handling

Always catch specific exceptions.
Don't use bare except clauses.

## Type Hints

Use type hints for function signatures.
"""


class TestDocumentLoader:
    def test_load_markdown(self):
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".md")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(SAMPLE_MARKDOWN)
            docs = DocumentLoader.load_markdown(path)
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

        assert len(docs) >= 2
        assert any("Naming" in d.metadata.get("section_title", "") for d in docs)

    def test_load_code_file(self):
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("def hello():\n    print('hello')\n")
            docs = DocumentLoader.load_code_file(path)
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

        assert len(docs) == 1
        assert docs[0].metadata["language"] == "python"
        assert docs[0].metadata["doc_type"] == "code"

    def test_load_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            md_path = os.path.join(tmpdir, "guide.md")
            with open(md_path, "w") as f:
                f.write(SAMPLE_MARKDOWN)

            py_path = os.path.join(tmpdir, "example.py")
            with open(py_path, "w") as f:
                f.write("x = 1\n")

            docs = DocumentLoader.load_directory(tmpdir)
            assert len(docs) >= 2

    def test_empty_markdown(self):
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".md")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("")
            docs = DocumentLoader.load_markdown(path)
        finally:
            if path and os.path.exists(path):
                os.unlink(path)

        assert len(docs) == 0
