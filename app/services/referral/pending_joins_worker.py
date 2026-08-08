"""T-022 · Pending InviteJoin worker.

Anti-fraud grace period tugagan `InviteJoin` yozuvlarini periodic ravishda
skanerlaydi va ular uchun:

  1. `pending_until = NULL`, `is_counted = True` deb yozadi.
  2. `InviteLink.join_count` ni atomik oshiradi.
  3. Invite egasi uchun `evaluate_user_rewards` chaqiradi.
  4. Yangi qozonilgan reward tier'lari bo'lsa Telegram orqali tabriknoma yuboradi.

Ishlash uslubi loyihaning mavjud `_reengagement_loop` pattern'iga o'xshash:
`asyncio.create_task` bilan lifespan ichida ishga tushirilib, shutdown'da
`task.cancel()` qilinadi.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import session_factory
from models.base import TASHKENT_TZ
from models.referral import InviteJoin, InviteLink
from models.rewards import RewardTier
from models.telegram_user import TelegramUser
from services.referral.rewards import evaluate_user_rewards

logger = logging.getLogger(__name__)

# Har necha soniyada bir marta scan. Grace period daqiqalarda (10+), shuning
# uchun 60 soniya kechikish qabul qilinadigan.
PENDING_SCAN_INTERVAL_SECONDS: int = 60


async def _promote_one(
    session: AsyncSession, join: InviteJoin
) -> tuple[int | None, list[RewardTier]]:
    """Bitta pending join'ni counted holatiga o'tkazadi.

    Returns:
        (inviter_tg_id, newly_earned_rewards). Agar biror sabab bilan yozuv
        allaqachon yakuniy holatga o'tgan bo'lsa (masalan, quick_leave), (None, []).
    """
    # `left_at` yoki `is_counted=True` bo'lsa boshqa jarayon allaqachon
    # yakunlagan — hech nima qilmaymiz.
    if join.left_at is not None or join.is_counted or join.pending_until is None:
        return None, []

    invite_link = await session.get(InviteLink, join.invite_link_id)
    if invite_link is None:
        # Link o'chirilgan — yozuvni yakunlaymiz.
        join.pending_until = None
        join.reject_reason = "link_missing"
        return None, []

    join.is_counted = True
    join.pending_until = None
    join.reject_reason = None
    # Atomik increment (session.execute update ishlatib).
    from sqlalchemy import update as sa_update

    await session.execute(
        sa_update(InviteLink)
        .where(InviteLink.id == invite_link.id)
        .values(join_count=InviteLink.join_count + 1)
    )

    owner = await session.get(TelegramUser, invite_link.user_id)
    new_rewards = await evaluate_user_rewards(session, invite_link.user_id)
    inviter_tg_id = owner.telegram_id if owner is not None else None
    return inviter_tg_id, new_rewards


async def scan_pending_joins_once() -> list[tuple[int, list[RewardTier]]]:
    """Bir marta scan — grace period tugagan barcha yozuvlarni counted qiladi.

    Returns:
        Reward tabriknoma yuborilishi kerak bo'lgan `(inviter_tg_id, tiers)`
        juftliklari ro'yxati.
    """
    notifications: list[tuple[int, list[RewardTier]]] = []
    now = datetime.now(TASHKENT_TZ)

    async with session_factory() as session:
        stmt = (
            select(InviteJoin)
            .where(
                InviteJoin.pending_until.is_not(None),
                InviteJoin.pending_until <= now,
                InviteJoin.is_counted.is_(False),
                InviteJoin.left_at.is_(None),
            )
            .limit(200)
        )
        rows = (await session.execute(stmt)).scalars().all()
        if not rows:
            return notifications

        for join in rows:
            try:
                inviter_tg_id, rewards = await _promote_one(session, join)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "pending_worker: promote xatosi join_id=%s", join.id
                )
                continue
            if inviter_tg_id is not None and rewards:
                notifications.append((inviter_tg_id, rewards))

        await session.commit()
        logger.info(
            "pending_worker: %d ta yozuv promoted, %d ta tabriknoma navbatda",
            len(rows),
            len(notifications),
        )

    return notifications


async def _notify_rewards(
    inviter_tg_id: int, rewards: list[RewardTier]
) -> None:
    """Reward tabriknomasini Telegram orqali yuboradi (best-effort)."""
    from bot.setup import bot  # local import — circular importdan qochish

    for tier in rewards:
        title = tier.title or f"{tier.required_invites} do'st"
        text = (
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            f"Siz <b>{title}</b> sovg'asini qozondingiz! 🏆\n\n"
        )
        if tier.description:
            text += f"{tier.description}\n\n"
        text += (
            "Sovg'angizni yetkazish uchun tez orada admin siz bilan bog'lanadi. 💝"
        )
        try:
            await bot.send_message(inviter_tg_id, text)
        except Exception:  # noqa: BLE001
            logger.exception(
                "pending_worker: reward tabriknoma yuborilmadi "
                "tg=%s tier_id=%s",
                inviter_tg_id,
                tier.id,
            )


async def pending_joins_loop() -> None:
    """Cheksiz loop — har `PENDING_SCAN_INTERVAL_SECONDS` da scan qiladi.

    `asyncio.CancelledError` shutdown paytida `task.cancel()` orqali keladi;
    loop uni yuqoriga uzatadi.
    """
    logger.info(
        "pending_joins_loop: ishga tushdi (interval=%ss)",
        PENDING_SCAN_INTERVAL_SECONDS,
    )
    while True:
        try:
            notifications = await scan_pending_joins_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("pending_joins_loop: scan xatosi")
            notifications = []

        for inviter_tg_id, rewards in notifications:
            try:
                await _notify_rewards(inviter_tg_id, rewards)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception(
                    "pending_joins_loop: notify xatosi tg=%s", inviter_tg_id
                )

        try:
            await asyncio.sleep(PENDING_SCAN_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            raise
