"""AI insight uchun Redis kesh (T-305).

Kalit: `insight:<profile_id>` → JSON. TTL 24 soat.
Redis mavjud bo'lmasa (dev/test) — kesh o'chirilgan hisoblanadi (miss).
"""
from __future__ import annotations

import json
import logging

from services.insights.ai_analyze import InsightResult

logger = logging.getLogger(__name__)

_TTL_SECONDS = 24 * 3600


def _key(profile_id: int) -> str:
    return f"insight:{profile_id}"


async def _get_redis():
    try:
        from api.v1.webapp import _redis
        return _redis
    except Exception:  # noqa: BLE001
        return None


async def get_cached_insight(profile_id: int) -> InsightResult | None:
    redis = await _get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(_key(profile_id))
    except Exception:
        logger.exception("insight cache GET xatosi (profile_id=%s)", profile_id)
        return None
    if not raw:
        return None
    try:
        return InsightResult.from_dict(json.loads(raw))
    except Exception:
        logger.exception("insight cache JSON parse xatosi")
        return None


async def set_cached_insight(profile_id: int, insight: InsightResult) -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        payload = json.dumps(insight.to_dict(), ensure_ascii=False)
        await redis.set(_key(profile_id), payload, ex=_TTL_SECONDS)
    except Exception:
        logger.exception("insight cache SET xatosi (profile_id=%s)", profile_id)


async def invalidate_cached_insight(profile_id: int) -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        await redis.delete(_key(profile_id))
    except Exception:
        logger.exception("insight cache DEL xatosi (profile_id=%s)", profile_id)
