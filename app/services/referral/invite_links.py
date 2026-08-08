"""Shaxsiy invite link generatsiyasi servisi.

Har bir (user, tracked_chat) juftligi uchun bitta faol Telegram invite link
yaratiladi va qayta ishlatiladi. Handler tanasi yupqa bo'lishi uchun barcha DB
va Telegram API logikasi shu yerda.
"""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessException, NotFoundException
from models.referral import InviteLink, TrackedChat

logger = logging.getLogger(__name__)


async def get_or_create_invite_link(
    session: AsyncSession,
    bot: Bot,
    *,
    user_id: int,
    tracked_chat_id: int,
) -> InviteLink:
    """`(user_id, tracked_chat_id)` uchun invite linkni oladi yoki yaratadi.

    Args:
        session: Async DB sessiya (handler tomonidan boshqariladi).
        bot: aiogram Bot instansi — `createChatInviteLink` chaqirig'i uchun.
        user_id: `telegram_users.id` (internal PK — Telegram TG ID emas).
        tracked_chat_id: `tracked_chats.id` (internal PK — Telegram chat_id emas).

    Returns:
        Faol (revoked_at IS NULL) `InviteLink` yozuvi.

    Raises:
        NotFoundException: TrackedChat topilmasa.
        BusinessException: Chat nofaol yoki Telegram API xatolik bersa.
    """
    tracked = await session.get(TrackedChat, tracked_chat_id)
    if tracked is None:
        raise NotFoundException(
            f"Kuzatiladigan chat topilmadi (id={tracked_chat_id})."
        )
    if not tracked.is_active:
        logger.info(
            "Invite link so'ralgan chat nofaol: tracked_chat_id=%s chat_id=%s",
            tracked_chat_id,
            tracked.chat_id,
        )
        raise BusinessException(
            "Bu kanal/guruh hozircha faol emas. Iltimos, keyinroq urinib ko'ring."
        )

    existing_stmt = select(InviteLink).where(
        InviteLink.user_id == user_id,
        InviteLink.tracked_chat_id == tracked_chat_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None and existing.revoked_at is None:
        return existing

    link_name = f"u{user_id}"
    # Kanallarda Telegram `chat_member` update yubormaydi — invite kuzatuvi
    # faqat `chat_join_request` orqali ishlaydi. Shuning uchun kanal uchun
    # `creates_join_request=True` bilan yaratamiz (bot avto tasdiqlaydi).
    creates_join_request = tracked.type == "channel"
    try:
        tg_link = await bot.create_chat_invite_link(
            chat_id=tracked.chat_id,
            name=link_name,
            creates_join_request=creates_join_request,
        )
    except TelegramRetryAfter as exc:
        logger.warning(
            "Telegram rate-limit: user_id=%s chat_id=%s retry_after=%s",
            user_id,
            tracked.chat_id,
            exc.retry_after,
        )
        raise BusinessException(
            "Telegram vaqtincha so'rovlarni cheklab qo'ydi. Bir oz kutib qayta urinib ko'ring."
        ) from exc
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        logger.error(
            "Invite link yaratib bo'lmadi (bot ruxsati yo'q?): "
            "user_id=%s chat_id=%s error=%s",
            user_id,
            tracked.chat_id,
            exc,
        )
        raise BusinessException(
            "Kanalda taklif linki yaratib bo'lmadi. Bot admin huquqlarini tekshiring."
        ) from exc
    except TelegramAPIError as exc:
        logger.exception(
            "Telegram API xatolik: user_id=%s chat_id=%s",
            user_id,
            tracked.chat_id,
        )
        raise BusinessException(
            "Telegram bilan aloqada xatolik yuz berdi. Keyinroq urinib ko'ring."
        ) from exc

    if existing is not None:
        # Ilgari yaratilgan, ammo revoke qilingan yozuv bor — yangilaymiz.
        existing.invite_link = tg_link.invite_link
        existing.telegram_link_name = link_name
        existing.join_count = 0
        existing.revoked_at = None
        invite = existing
        logger.info(
            "InviteLink qayta faollashtirildi: user_id=%s tracked_chat_id=%s",
            user_id,
            tracked_chat_id,
        )
    else:
        invite = InviteLink(
            user_id=user_id,
            tracked_chat_id=tracked_chat_id,
            invite_link=tg_link.invite_link,
            telegram_link_name=link_name,
            join_count=0,
        )
        session.add(invite)
        logger.info(
            "InviteLink yaratildi: user_id=%s tracked_chat_id=%s chat_id=%s",
            user_id,
            tracked_chat_id,
            tracked.chat_id,
        )

    await session.commit()
    await session.refresh(invite)
    return invite
