"""T-510 · Claude AI provider mock — schema validation.

Anthropic SDK'ning `messages.create` chaqiruvi monkeypatch qilinadi.
Real API kalit yoki tarmoq talab qilinmaydi.
"""
from __future__ import annotations

import types

import pytest

from services.ai.base import AIProviderError


class _FakeToolUseBlock:
    def __init__(self, name: str, input_: dict) -> None:
        self.type = "tool_use"
        self.name = name
        self.input = input_


class _FakeUsage:
    def __init__(self, in_tok: int, out_tok: int) -> None:
        self.input_tokens = in_tok
        self.output_tokens = out_tok


class _FakeResponse:
    def __init__(self, blocks, in_tok: int = 50, out_tok: int = 100) -> None:
        self.content = blocks
        self.usage = _FakeUsage(in_tok, out_tok)


class _FakeMessages:
    def __init__(self, response) -> None:
        self._response = response

    async def create(self, **kwargs):
        return self._response


class _FakeClient:
    def __init__(self, response) -> None:
        self.messages = _FakeMessages(response)


def _install_fake_client(monkeypatch, response) -> None:
    """Anthropic AsyncAnthropic'ni fake bilan almashtiramiz."""
    fake_module = types.SimpleNamespace(
        AsyncAnthropic=lambda **kw: _FakeClient(response),
    )
    monkeypatch.setitem(__import__("sys").modules, "anthropic", fake_module)


@pytest.mark.asyncio
async def test_claude_provider_parses_valid_tool_use(monkeypatch):
    payload = {
        "title": "AI test",
        "questions": [
            {
                "text": "1 plus 1 nechaga teng?",
                "option_a": "1", "option_b": "2",
                "option_c": "3", "option_d": "4",
                "correct_option": "B",
                "explanation": "Aniq: 1+1=2.",
            }
        ],
    }
    response = _FakeResponse([_FakeToolUseBlock("submit_quiz", payload)])
    _install_fake_client(monkeypatch, response)

    from services.ai.claude import ClaudeProvider
    provider = ClaudeProvider(api_key="fake", model="claude-x")
    result = await provider.generate_quiz("matn", num_questions=1)
    assert result.title == "AI test"
    assert len(result.questions) == 1
    assert result.questions[0].correct_option == "B"
    assert result.input_tokens == 50
    assert result.output_tokens == 100


@pytest.mark.asyncio
async def test_claude_provider_no_tool_use_raises(monkeypatch):
    response = _FakeResponse([])  # bo'sh
    _install_fake_client(monkeypatch, response)

    from services.ai.claude import ClaudeProvider
    provider = ClaudeProvider(api_key="fake", model="claude-x")
    with pytest.raises(AIProviderError, match="tool_use"):
        await provider.generate_quiz("matn")


@pytest.mark.asyncio
async def test_claude_provider_invalid_schema_raises(monkeypatch):
    # `correct_option` yaroqsiz — Pydantic rad etadi.
    payload = {
        "title": "T",
        "questions": [
            {
                "text": "?", "option_a": "a", "option_b": "b",
                "option_c": "c", "option_d": "d",
                "correct_option": "Z",  # noqa
            }
        ],
    }
    response = _FakeResponse([_FakeToolUseBlock("submit_quiz", payload)])
    _install_fake_client(monkeypatch, response)

    from services.ai.claude import ClaudeProvider
    provider = ClaudeProvider(api_key="fake", model="claude-x")
    with pytest.raises(AIProviderError, match="Yaroqsiz"):
        await provider.generate_quiz("matn")


def test_claude_provider_empty_key_raises():
    from services.ai.claude import ClaudeProvider
    with pytest.raises(AIProviderError):
        ClaudeProvider(api_key="", model="claude-x")
