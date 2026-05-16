"""Tests for configuration settings."""

import pytest
from src.config import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings()
        # claude_model may be overridden by .env, so just check it's a non-empty string
        assert isinstance(s.claude_model, str) and len(s.claude_model) > 0
        assert s.confidence_threshold == 0.6
        assert s.max_context_tokens == 8000
        assert s.temperature == 0.0
        assert s.log_level == "INFO"

    def test_language_map_python(self):
        s = Settings()
        assert s.language_map[".py"] == "python"

    def test_language_map_javascript(self):
        s = Settings()
        assert s.language_map[".js"] == "javascript"
        assert s.language_map[".jsx"] == "javascript"

    def test_language_map_typescript(self):
        s = Settings()
        assert s.language_map[".ts"] == "typescript"
        assert s.language_map[".tsx"] == "typescript"

    def test_language_map_c_family(self):
        s = Settings()
        assert s.language_map[".c"] == "c"
        assert s.language_map[".h"] == "c"
        assert s.language_map[".cpp"] == "cpp"
        assert s.language_map[".cs"] == "c_sharp"

    def test_language_map_structured_text(self):
        s = Settings()
        assert s.language_map[".st"] == "structured_text"
        assert s.language_map[".iecst"] == "structured_text"
        assert s.language_map[".l5x"] == "structured_text"
        assert s.language_map[".smc2"] == "structured_text"

    def test_treesitter_languages_includes_common(self):
        s = Settings()
        assert "python" in s.treesitter_languages
        assert "javascript" in s.treesitter_languages
        assert "typescript" in s.treesitter_languages
        assert "java" in s.treesitter_languages
        assert "go" in s.treesitter_languages
        assert "rust" in s.treesitter_languages

    def test_project_root_property(self):
        s = Settings()
        root = s.project_root
        assert root.is_dir()

    def test_guidelines_dir_property(self):
        s = Settings()
        assert "guidelines" in str(s.guidelines_dir)

    def test_embedding_model_default(self):
        s = Settings()
        assert s.embedding_model == "all-MiniLM-L6-v2"
