"""Application configuration using pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic API (also supports compatible endpoints like Mimo)
    anthropic_api_key: str = ""
    anthropic_base_url: str | None = None  # Custom API endpoint (e.g. Mimo)
    claude_model: str = "claude-sonnet-4-20250514"
    disable_thinking: bool = False  # Set True for Mimo/reasoning models

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"

    # Vector store
    vectorstore_dir: str = "./data/vectorstore"

    # Review settings
    confidence_threshold: float = 0.6
    max_context_tokens: int = 8000
    temperature: float = 0.0

    # Supported languages mapping (extension -> language name)
    language_map: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "c_sharp",
        ".php": "php",
        ".rb": "ruby",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".scala": "scala",
        ".sc": "scala",
        ".lua": "lua",
        ".sql": "sql",
        ".jl": "julia",
        ".m": "matlab",
        ".dart": "dart",
        ".st": "structured_text",
        ".iecst": "structured_text",
        ".l5x": "structured_text",
        ".smc2": "structured_text",
        ".cob": "cobol",
        ".cbl": "cobol",
        ".cpy": "cobol",
        ".r": "r",
        ".sas": "sas",
        ".sol": "solidity",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".v": "verilog",
        ".vh": "verilog",
        ".sv": "verilog",
        ".svh": "verilog",
        ".zig": "zig",
        ".mm": "objective_c",
    }

    # Tree-sitter supported languages (subset that we have grammars for)
    treesitter_languages: list[str] = [
        "python", "javascript", "typescript", "c_sharp",
        "java", "go", "rust", "c", "cpp",
        "php", "ruby", "swift", "kotlin", "scala",
        "lua", "sql", "julia", "matlab",
        "solidity", "shell", "verilog", "zig", "objective_c",
    ]

    # Logging
    log_level: str = "INFO"

    # Custom guidelines
    custom_guidelines_dir: str = "./data/custom_guidelines"
    max_upload_size_mb: int = 10
    allowed_upload_extensions: list[str] = [
        ".md", ".txt", ".rst", ".adoc", ".pdf", ".docx"
    ]

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def guidelines_dir(self) -> Path:
        return self.project_root / "data" / "guidelines"

    @property
    def vectorstore_path(self) -> Path:
        return Path(self.vectorstore_dir)

    @property
    def custom_guidelines_path(self) -> Path:
        return Path(self.custom_guidelines_dir)


settings = Settings()
