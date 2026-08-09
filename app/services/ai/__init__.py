"""AI provider abstraksiyasi. `.env` `AI_PROVIDER` bo'yicha tanlanadi."""
from __future__ import annotations

from functools import lru_cache

from core.config import settings
from services.ai.base import AIProvider


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    name = (settings.AI_PROVIDER or "claude").lower()
    if name == "claude":
        from services.ai.claude import ClaudeProvider

        return ClaudeProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.AI_MODEL,
        )
    raise ValueError(f"Noma'lum AI_PROVIDER: {name}")
