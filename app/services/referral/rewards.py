"""T-021 · Referral sovg'a (reward) tizimi servisi.

`evaluate_user_rewards` — foydalanuvchining jami taklif soni (barcha
tracked_chat'lar bo'yicha `SUM(InviteLink.join_count)`) hisoblab, unga mos
keladigan barcha aktiv `RewardTier`'lar uchun `UserReward` yozadi.
Idempotent: mavjud bo'lgan yozuvlar `INSERT ... ON CONFLICT DO NOTHING`
orqali skip qilinadi. Return: **shu chaqiruvda yangi qozonilgan** tier'lar
ro'yxati (bot tomonidan tabriknoma yuborish uchun).
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.base import TASHKENT_TZ
from models.referral import InviteLink
from models.rewards import RewardTier, UserReward

logger = logging.getLogger(__name__)


async def _get_user_total_invites(session: AsyncSession, user_id: int) -> int:
    """Foydalanuvchining barcha faol invite linklari bo'yicha jami join_count."""
    stmt = select(
        func.coalesce(func.sum(InviteLink.join_count), 0)
    ).where(
        InviteLink.user_id == user_id,
        InviteLink.revoked_at.is_(None),
    )
    total = (await session.execute(stmt)).scalar_one()
    return int(total or 0)


async def evaluate_user_rewards(
    session: AsyncSession, user_id: int
) -> list[RewardTier]:
    """Foydalanuvchi uchun yetib olingan reward tier'larni yozadi.

    Idempotent: `ON CONFLICT (user_id, reward_tier_id) DO NOTHING` — mavjud
    yozuvlar tegilmaydi. Return qiymati faqat **shu chaqiruvda yangi
    yaratilgan** tier'larni beradi, shuning uchun bot tabriknomasini bir
    marta yuboradi.

    Muhim: bu funksiya `record_join` ichida chaqiriladi va o'z tranzaktsiyasini
    boshqarmaydi (chaqiruvchi commit qiladi). RETURNING id yordamida qaysi
    yozuvlar aslida INSERT bo'lganini aniqlaymiz.
    """
    total_invites = await _get_user_total_invites(session, user_id)
    if total_invites <= 0:
        return []

    tiers_stmt = (
        select(RewardTier)
        .where(
            RewardTier.is_active.is_(True),
            RewardTier.required_invites <= total_invites,
        )
        .order_by(RewardTier.required_invites.asc())
    )
    eligible_tiers = (await session.execute(tiers_stmt)).scalars().all()
    if not eligible_tiers:
        return []

    now = datetime.now(TASHKENT_TZ)
    rows = [
        {
            "user_id": user_id,
            "reward_tier_id": tier.id,
            "earned_at": now,
        }
        for tier in eligible_tiers
    ]

    insert_stmt = (
        pg_insert(UserReward)
        .values(rows)
        .on_conflict_do_nothing(
            constraint="uq_user_rewards_user_tier"
        )
        .returning(UserReward.reward_tier_id)
    )
    try:
        result = await session.execute(insert_stmt)
    except Exception:  # noqa: BLE001
        # Xatolik yuz bersa reward mexanizmi record_join'ni yiqitmasin.
        logger.exception(
            "evaluate_user_rewards: INSERT xatosi user_id=%s", user_id
        )
        return []

    inserted_tier_ids = {row[0] for row in result.all()}
    if not inserted_tier_ids:
        return []

    newly_earned = [t for t in eligible_tiers if t.id in inserted_tier_ids]
    logger.info(
        "evaluate_user_rewards: user_id=%s total=%s yangi tier'lar=%s",
        user_id,
        total_invites,
        [t.id for t in newly_earned],
    )
    return newly_earned
