"""Config API routes."""

from fastapi import APIRouter

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings

router = APIRouter()


@router.get("/")
def get_config():
    """Get current configuration."""
    return {
        "claude_model": settings.claude_model,
        "confidence_threshold": settings.confidence_threshold,
        "max_context_tokens": settings.max_context_tokens,
        "temperature": settings.temperature,
        "log_level": settings.log_level,
        "supported_languages": list(settings.language_map.values()),
        "anthropic_base_url": settings.anthropic_base_url or "",
    }


@router.get("/languages")
def get_languages():
    """Get supported languages with file extensions."""
    return [
        {"language": lang, "extensions": [ext for ext, l in settings.language_map.items() if l == lang]}
        for lang in sorted(set(settings.language_map.values()))
    ]
