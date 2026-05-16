"""Pytest fixtures for the test suite."""

import os
import tempfile

import pytest


@pytest.fixture
def sample_diff():
    """A sample unified diff for testing."""
    return """\
--- a/app.py
+++ b/app.py
@@ -1,5 +1,6 @@
 def hello():
-    print('hello')
+    print('hello world')
+    return True

 def goodbye():
     print('goodbye')
"""


@pytest.fixture
def sample_python_file():
    """Sample Python source code for AST testing."""
    return """\
import os
from pathlib import Path

class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a: int, b: int) -> int:
        result = a + b
        self.history.append(("add", a, b, result))
        return result

    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

def utility():
    return Path.cwd()
"""


@pytest.fixture
def sample_guidelines():
    """Sample coding guidelines markdown."""
    return """\
# Python Coding Guidelines

## Error Handling

Always handle specific exceptions, never use bare `except`.
Use custom exception classes for domain errors.

## Naming

- Functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Private: prefix with underscore

## Type Hints

All public functions must have type hints.
Use `Optional[X]` instead of `X | None` for Python < 3.10.
"""


@pytest.fixture
def temp_repo_dir():
    """Create a temporary directory for test repos."""
    with tempfile.TemporaryDirectory(prefix="test-review-") as tmpdir:
        yield tmpdir
