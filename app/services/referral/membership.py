"""A'zolik (subscription) gate servisi.

Foydalanuvchi bot admin bo'lgan **barcha faol** tracked chatlarga a'zomi yoki
yo'qligini `bot.get_chat_member` orqali tekshiradi. Handler tanasi yupqa qolishi
uchun barcha logika shu yerda. Hech qanday exception tashqariga chiqmaydi —
xatolik "a'zo emas" deb talqin qilinadi.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from sqlalchemy.ext.asyncio import AsyncSession

from models.referral import TrackedChat
from services.referral.events import get_active_tracked_chats

logger = logging.getLogger(__name__)

# Foydalanuvchi chat a'zosi hisoblanadigan statuslar.
_MEMBER_STATUSES: frozenset[str] = frozenset(
    {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }
)


async def _is_member(bot: Bot, *, chat_id: int, user_tg_id: int) -> bool:
    """Bitta chatda foydalanuvchi a'zoligini tekshiradi (xatolik = a'zo emas)."""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_tg_id)
    except Exception:  # noqa: BLE001
        logger.info(
            "get_chat_member xatolik: chat_id=%s user=%s (a'zo emas deb olindi)",
            chat_id,
            user_tg_id,
        )
        return False

    status = member.status
    if status in _MEMBER_STATUSES:
        return True
    # RESTRICTED holatida foydalanuvchi hali chatda bo'lishi mumkin.
    if status == ChatMemberStatus.RESTRICTED:
        return bool(getattr(member, "is_member", False))
    return False


async def check_subscription(
    session: AsyncSession, bot: Bot, *, user_tg_id: int
) -> tuple[bool, list[TrackedChat]]:
    """Barcha faol tracked chatlar bo'yicha a'zolikni tekshiradi.

    Returns:
        `(ok, missing)` — `ok` barcha chatlarga a'zo bo'lsa True; `missing` esa
        foydalanuvchi hali qo'shilmagan chatlar ro'yxati. Faol chat bo'lmasa
        `(True, [])` qaytadi.
    """
    chats = await get_active_tracked_chats(session)
    if not chats:
        return (True, [])
    # Barcha chatlarga bir vaqtda so'rov — sequential loop 3× latency edi.
    results = await asyncio.gather(
        *(
            _is_member(bot, chat_id=c.chat_id, user_tg_id=user_tg_id)
            for c in chats
        ),
        return_exceptions=False,
    )
    missing = [c for c, ok in zip(chats, results) if not ok]
    return (not missing, missing)
