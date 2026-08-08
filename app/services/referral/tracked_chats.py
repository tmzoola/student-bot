"""TrackedChat upsert / deactivate xizmatlari.

`my_chat_member` hodisasi asosida chaqiriladi (T-015). Handler tanasi yupqa
bo'lishi uchun barcha DB logikasi shu yerda.
"""
from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.referral import TrackedChat

logger = logging.getLogger(__name__)

TrackedChatType = Literal["group", "supergroup", "channel"]


async def upsert_tracked_chat(
    session: AsyncSession,
    *,
    chat_id: int,
    title: str,
    chat_type: TrackedChatType,
    username: str | None,
    is_active: bool,
) -> TrackedChat:
    """Chatni jadvalga yozadi yoki mavjudini yangilaydi.

    `is_active` chaqiruvchi tomondan hisoblab beriladi (masalan, admin +
    `can_invite_users=True` bo'lsa `True`).
    """
    result = await session.execute(
        select(TrackedChat).where(TrackedChat.chat_id == chat_id)
    )
    tracked = result.scalar_one_or_none()

    if tracked is None:
        # Birinchi marta qo'shilganda chat har doim nofaol holatda yoziladi —
        # admin qo'lda faollashtirmaguncha referral hisoblash boshlanmaydi.
        tracked = TrackedChat(
            chat_id=chat_id,
            title=title[:255],
            type=chat_type,
            username=username,
            is_active=False,
        )
        session.add(tracked)
        logger.info(
            "TrackedChat yaratildi (nofaol): chat_id=%s title=%r type=%s "
            "(hisoblangan is_active=%s e'tiborsiz qoldirildi)",
            chat_id,
            title,
            chat_type,
            is_active,
        )
    else:
        tracked.title = title[:255]
        tracked.type = chat_type
        tracked.username = username
        tracked.is_active = is_active
        logger.info(
            "TrackedChat yangilandi: chat_id=%s active=%s title=%r",
            chat_id,
            is_active,
            title,
        )

    await session.commit()
    await session.refresh(tracked)
    return tracked


async def deactivate_tracked_chat(
    session: AsyncSession,
    *,
    chat_id: int,
    reason: str,
) -> None:
    """Chatni soft-deactivate qiladi. Jadval yozuvi bo'lmasa hech narsa qilmaydi."""
    result = await session.execute(
        select(TrackedChat).where(TrackedChat.chat_id == chat_id)
    )
    tracked = result.scalar_one_or_none()
    if tracked is None:
        logger.debug(
            "deactivate_tracked_chat: chat_id=%s jadvalda topilmadi (%s)",
            chat_id,
            reason,
        )
        return
    if not tracked.is_active:
        logger.debug(
            "TrackedChat allaqachon nofaol: chat_id=%s (%s)", chat_id, reason
        )
        return
    tracked.is_active = False
    await session.commit()
    logger.info(
        "TrackedChat nofaollashtirildi: chat_id=%s sabab=%s", chat_id, reason
    )
