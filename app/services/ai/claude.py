"""Anthropic Claude provider. Tool use orqali structured JSON qaytaradi."""
from __future__ import annotations

import logging

from services.ai.base import AIProvider, AIProviderError
from services.ai.prompts import QUIZ_TOOL_SCHEMA, SYSTEM_PROMPT, build_user_prompt
from services.ai.schemas import QuizGenResult

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise AIProviderError("ANTHROPIC_API_KEY bo'sh")
        # Lazy import — anthropic o'rnatilmagan muhitda ham modul yuklanadi.
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key, timeout=120.0)
        self._model = model

    async def generate_quiz(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        language: str = "uz",
    ) -> QuizGenResult:
        user_prompt = build_user_prompt(text, num_questions, difficulty, language)

        # System prompt uzun bo'lsa cache'lash (1024+ token). Bizniki qisqa,
        # ammo API ruxsat beradi — kelajakda uzaytirishga tayyor.
        system_blocks = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=8000,
                system=system_blocks,
                tools=[QUIZ_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "submit_quiz"},
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            logger.exception("Claude API xatosi")
            raise AIProviderError(f"Claude chaqiruv xatosi: {exc}") from exc

        tool_input: dict | None = None
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "submit_quiz":
                tool_input = block.input
                break

        if tool_input is None:
            raise AIProviderError("Claude tool_use bloki qaytarmadi")

        usage = getattr(response, "usage", None)
        in_tok = int(getattr(usage, "input_tokens", 0) or 0)
        out_tok = int(getattr(usage, "output_tokens", 0) or 0)

        logger.info(
            "ai_call_cost provider=claude model=%s input_tokens=%d output_tokens=%d",
            self._model,
            in_tok,
            out_tok,
        )

        try:
            result = QuizGenResult(
                title=tool_input["title"],
                questions=tool_input["questions"],
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
        except Exception as exc:
            logger.exception("Claude javobini validate qilib bo'lmadi: %s", tool_input)
            raise AIProviderError(f"Yaroqsiz javob strukturasi: {exc}") from exc

        return result
