"""T-303 · generate_insight — AI provider mock qilinadi."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.ai.base import AIProviderError
from services.insights import ai_analyze
from services.insights.ai_analyze import InsightResult, generate_insight
from services.insights.stats import SubjectStat, TopicStat, TrendPoint, UserStats


class _FakeAnthropic:
    def __init__(self, response) -> None:
        self._response = response
        self.messages = SimpleNamespace(create=self._create)

    def __call__(self, *args, **kwargs):  # act as factory
        return self

    async def _create(self, **kwargs):
        return self._response


def _resp(tool_input: dict | None):
    blocks = []
    if tool_input is not None:
        blocks.append(SimpleNamespace(type="tool_use", name="submit_insight", input=tool_input))
    return SimpleNamespace(
        content=blocks,
        usage=SimpleNamespace(input_tokens=42, output_tokens=17),
    )


def _profile_stub():
    return SimpleNamespace(
        full_name="Ali Valiyev",
        course_number=2,
        semester=1,
        faculty=SimpleNamespace(name="Kompyuter"),
    )


def _stats_stub():
    return UserStats(
        attempts_total=10,
        overall_accuracy_pct=62,
        by_topic=[
            TopicStat(1, "Mexanika", "Fizika", 3, 3, 6, 33),
            TopicStat(2, "Chiziqli", "Matem", 3, 8, 1, 89),
        ],
        by_subject=[
            SubjectStat(1, "Fizika", 3, 3, 6, 33),
            SubjectStat(2, "Matem", 3, 8, 1, 89),
        ],
        recent_trend=[TrendPoint("2026-08-03", 5, 60)],
        top_weaknesses=[TopicStat(1, "Mexanika", "Fizika", 3, 3, 6, 33)],
        top_strengths=[TopicStat(2, "Chiziqli", "Matem", 3, 8, 1, 89)],
    )


@pytest.mark.asyncio
async def test_generate_insight_happy(monkeypatch):
    monkeypatch.setattr(ai_analyze.settings, "AI_PROVIDER", "claude")
    monkeypatch.setattr(ai_analyze.settings, "ANTHROPIC_API_KEY", "xxx")

    tool_input = {
        "summary": "Umumiy natijalar o'rtacha.",
        "weaknesses": [{"topic": "Mexanika", "tip": "3 kun ichida 2 test yech", "accuracy": 33}],
        "strengths": [{"topic": "Chiziqli", "accuracy": 89}],
        "recommendations": ["Har kuni 20 daqiqa mashq"],
    }
    fake = _FakeAnthropic(_resp(tool_input))
    import services.insights.ai_analyze as mod
    # anthropic.AsyncAnthropic ni patch qilamiz — u lazy import qilinadi.
    import sys
    fake_pkg = SimpleNamespace(AsyncAnthropic=lambda **kw: fake)
    monkeypatch.setitem(sys.modules, "anthropic", fake_pkg)

    res = await generate_insight(_stats_stub(), _profile_stub())  # type: ignore[arg-type]
    assert isinstance(res, InsightResult)
    assert res.summary.startswith("Umumiy")
    assert res.weaknesses[0].topic == "Mexanika"
    assert res.weaknesses[0].tip.startswith("3 kun")
    assert res.strengths[0].topic == "Chiziqli"
    assert res.recommendations == ["Har kuni 20 daqiqa mashq"]
    assert res.input_tokens == 42
    assert res.output_tokens == 17


@pytest.mark.asyncio
async def test_generate_insight_no_tool_use(monkeypatch):
    monkeypatch.setattr(ai_analyze.settings, "AI_PROVIDER", "claude")
    monkeypatch.setattr(ai_analyze.settings, "ANTHROPIC_API_KEY", "xxx")

    import sys
    fake = _FakeAnthropic(_resp(None))
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AsyncAnthropic=lambda **kw: fake))

    with pytest.raises(AIProviderError):
        await generate_insight(_stats_stub(), _profile_stub())  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_generate_insight_empty_api_key(monkeypatch):
    monkeypatch.setattr(ai_analyze.settings, "AI_PROVIDER", "claude")
    monkeypatch.setattr(ai_analyze.settings, "ANTHROPIC_API_KEY", "")

    with pytest.raises(AIProviderError):
        await generate_insight(_stats_stub(), _profile_stub())  # type: ignore[arg-type]


def test_insight_result_dict_roundtrip():
    r = InsightResult(
        summary="x",
        weaknesses=[ai_analyze.WeaknessItem("A", "tip1", 30)],
        strengths=[ai_analyze.StrengthItem("B", 90)],
        recommendations=["do X"],
        input_tokens=1, output_tokens=2,
    )
    d = r.to_dict()
    r2 = InsightResult.from_dict(d)
    assert r2.summary == "x"
    assert r2.weaknesses[0].topic == "A"
    assert r2.strengths[0].accuracy == 90
    assert r2.recommendations == ["do X"]
