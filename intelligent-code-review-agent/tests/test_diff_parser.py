"""Tests for the diff parser module."""

import pytest
from src.git.diff_parser import DiffParser
from src.git.models import DiffHunk, DiffLine


SAMPLE_DIFF = """\
--- a/app.py
+++ b/app.py
@@ -1,5 +1,6 @@
 def hello():
-    print('hello')
+    print('hello world')
+    return True

 def goodbye():
     print('goodbye')
@@ -10,3 +11,5 @@
 def add(a, b):
-    return a + b
+    result = a + b
+    print(f"Adding {a} + {b}")
+    return result
"""


class TestDiffParser:
    def test_parse_hunk_count(self):
        hunks = DiffParser.parse_unified_diff(SAMPLE_DIFF)
        assert len(hunks) == 2

    def test_parse_hunk_header(self):
        hunks = DiffParser.parse_unified_diff(SAMPLE_DIFF)
        assert hunks[0].old_start == 1
        assert hunks[0].new_start == 1
        assert hunks[1].old_start == 10
        assert hunks[1].new_start == 11

    def test_parse_added_lines(self):
        hunks = DiffParser.parse_unified_diff(SAMPLE_DIFF)
        added = hunks[0].added_lines
        assert len(added) >= 1
        assert any("hello world" in line.content for line in added)

    def test_parse_deleted_lines(self):
        hunks = DiffParser.parse_unified_diff(SAMPLE_DIFF)
        deleted = hunks[0].deleted_lines
        assert len(deleted) >= 1
        assert any("hello" in line.content and "world" not in line.content for line in deleted)

    def test_parse_context_lines(self):
        hunks = DiffParser.parse_unified_diff(SAMPLE_DIFF)
        context = [l for l in hunks[0].lines if not l.is_added and not l.is_deleted]
        assert len(context) >= 1

    def test_changed_range_new(self):
        hunks = DiffParser.parse_unified_diff(SAMPLE_DIFF)
        start, end = hunks[0].changed_range_new
        assert start >= 1
        assert end >= start

    def test_extract_changed_line_ranges(self):
        hunks = DiffParser.parse_unified_diff(SAMPLE_DIFF)
        ranges = DiffParser.extract_changed_line_ranges(hunks)
        assert len(ranges) == 2
        assert all(isinstance(r, tuple) and len(r) == 2 for r in ranges)

    def test_empty_diff(self):
        hunks = DiffParser.parse_unified_diff("")
        assert len(hunks) == 0

    def test_single_line_change(self):
        diff = """\
--- a/test.py
+++ b/test.py
@@ -1 +1 @@
-old
+new
"""
        hunks = DiffParser.parse_unified_diff(diff)
        assert len(hunks) == 1
        assert hunks[0].added_lines[0].content == "new"
        assert hunks[0].deleted_lines[0].content == "old"
