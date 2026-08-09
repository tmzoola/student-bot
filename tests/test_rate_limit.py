"""T-509 · AI kunlik rate limit — Redis mock bilan."""
from __future__ import annotations

import pytest
from fastapi import HTTPException


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    def pipeline(self):
        outer = self

        class _Pipe:
            def __init__(self):
                self.cmds: list = []

            def incr(self, key, amt=1):
                self.cmds.append(("incr", key, amt))
                return self

            def expire(self, key, ttl):
                self.cmds.append(("expire", key, ttl))
                return self

            async def execute(self):
                results = []
                for cmd in self.cmds:
                    if cmd[0] == "incr":
                        outer.store[cmd[1]] = outer.store.get(cmd[1], 0) + cmd[2]
                        results.append(outer.store[cmd[1]])
                    elif cmd[0] == "expire":
                        results.append(True)
                return results

        return _Pipe()

    async def get(self, key):
        v = self.store.get(key)
        return str(v) if v is not None else None


@pytest.mark.asyncio
async def test_rate_limit_increments_under_limit(monkeypatch):
    from services import ai_rate_limit
    fake = _FakeRedis()

    async def _get_redis():
        return fake
    monkeypatch.setattr(ai_rate_limit, "_get_redis", _get_redis)

    from core.config import settings
    monkeypatch.setattr(settings, "AI_DAILY_LIMIT_PER_USER", 3)

    assert await ai_rate_limit.check_and_increment_daily(1) == 1
    assert await ai_rate_limit.check_and_increment_daily(1) == 2
    assert await ai_rate_limit.check_and_increment_daily(1) == 3


@pytest.mark.asyncio
async def test_rate_limit_over_raises_429(monkeypatch):
    from services import ai_rate_limit
    fake = _FakeRedis()

    async def _get_redis():
        return fake
    monkeypatch.setattr(ai_rate_limit, "_get_redis", _get_redis)

    from core.config import settings
    monkeypatch.setattr(settings, "AI_DAILY_LIMIT_PER_USER", 2)

    await ai_rate_limit.check_and_increment_daily(7)
    await ai_rate_limit.check_and_increment_daily(7)
    with pytest.raises(HTTPException) as exc:
        await ai_rate_limit.check_and_increment_daily(7)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_no_redis_bypasses(monkeypatch):
    from services import ai_rate_limit

    async def _get_redis():
        return None
    monkeypatch.setattr(ai_rate_limit, "_get_redis", _get_redis)
    # Limit past 0 — lekin redis yo'q, o'tkazib yuborilishi kerak.
    assert await ai_rate_limit.check_and_increment_daily(99) == 0
