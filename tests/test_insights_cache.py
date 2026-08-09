"""T-305 · Insight Redis kesh — fake Redis bilan."""
from __future__ import annotations

import pytest

from services.insights import cache as cache_mod
from services.insights.ai_analyze import InsightResult, StrengthItem, WeaknessItem


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, k):
        return self.store.get(k)

    async def set(self, k, v, ex=None):
        self.store[k] = v
        if ex is not None:
            self.ttls[k] = int(ex)

    async def delete(self, k):
        self.store.pop(k, None)
        self.ttls.pop(k, None)


@pytest.mark.asyncio
async def test_cache_miss_when_no_redis(monkeypatch):
    async def _no_redis():
        return None
    monkeypatch.setattr(cache_mod, "_get_redis", _no_redis)
    assert await cache_mod.get_cached_insight(1) is None
    # Set — no-op, no error
    await cache_mod.set_cached_insight(1, InsightResult(summary="x", recommendations=["y"]))


@pytest.mark.asyncio
async def test_cache_set_get_roundtrip(monkeypatch):
    fake = _FakeRedis()

    async def _get():
        return fake
    monkeypatch.setattr(cache_mod, "_get_redis", _get)

    original = InsightResult(
        summary="Xulosa",
        weaknesses=[WeaknessItem("Mexanika", "test", 33)],
        strengths=[StrengthItem("Matem", 89)],
        recommendations=["Kuniga 1 test"],
        input_tokens=10, output_tokens=20,
    )
    await cache_mod.set_cached_insight(42, original)

    got = await cache_mod.get_cached_insight(42)
    assert got is not None
    assert got.summary == "Xulosa"
    assert got.weaknesses[0].tip == "test"
    assert got.strengths[0].topic == "Matem"
    assert got.recommendations == ["Kuniga 1 test"]
    # TTL 24h yozildi
    assert fake.ttls["insight:42"] == 24 * 3600


@pytest.mark.asyncio
async def test_cache_invalidate(monkeypatch):
    fake = _FakeRedis()

    async def _get():
        return fake
    monkeypatch.setattr(cache_mod, "_get_redis", _get)

    await cache_mod.set_cached_insight(7, InsightResult(summary="s", recommendations=["r"]))
    assert await cache_mod.get_cached_insight(7) is not None
    await cache_mod.invalidate_cached_insight(7)
    assert await cache_mod.get_cached_insight(7) is None
