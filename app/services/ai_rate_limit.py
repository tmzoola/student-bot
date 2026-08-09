"""AI generatsiya uchun kunlik rate limit (T-509).

Redis'da counter `ai:daily:<profile_id>:<YYYY-MM-DD>` saqlanadi, TTL 24
soat. Har material yuklashda increment qilinadi; limit oshsa 429 xato.

Redis mavjud bo'lmasa (test/local dev) — tekshiruv o'tkazib yuboriladi
(logga warn yoziladi). Prod'da Redis majburiy.
"""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import HTTPException

from core.config import settings

logger = logging.getLogger(__name__)


def _today_key(profile_id: int) -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return f"ai:daily:{profile_id}:{today}"


async def _get_redis():
    try:
        from api.v1.webapp import _redis
        return _redis
    except Exception:  # noqa: BLE001
        return None


async def check_and_increment_daily(profile_id: int) -> int:
    """Atomik INCR + EXPIRE. Limit oshsa `HTTPException(429)`.

    Return: joriy sanaga qadar bo'lgan chaqiruvlar soni (increment'dan keyin).
    """
    redis = await _get_redis()
    if redis is None:
        logger.warning("rate_limit: Redis mavjud emas — o'tkazib yuborildi (profile_id=%s)", profile_id)
        return 0

    key = _today_key(profile_id)
    try:
        # Pipeline: INCR va EXPIRE (24h) atomik.
        pipe = redis.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, 24 * 3600)
        results = await pipe.execute()
        count = int(results[0])
    except Exception:
        logger.exception("rate_limit: Redis INCR xatosi — o'tkazib yuborildi")
        return 0

    limit = settings.AI_DAILY_LIMIT_PER_USER
    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Kunlik AI limit tugadi ({limit}). Ertaga qayta urinib ko'ring.",
        )
    return count


async def current_daily_count(profile_id: int) -> int:
    redis = await _get_redis()
    if redis is None:
        return 0
    try:
        val = await redis.get(_today_key(profile_id))
        return int(val) if val else 0
    except Exception:
        return 0
