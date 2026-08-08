"""T-015 · `my_chat_member` handler.

Bot bir chatga qo'shilganda / adminlik statusi o'zgarganda TrackedChat
jadvalini avtomatik sinxronlashtiradi. Faqat guruh, supergruh va kanallar
kuzatiladi (private chatlar e'tiborga olinmaydi).

Muhim: har qanday holatda ham exception ko'tarmasligimiz kerak — aks holda
Telegram bir xil update'ni qayta-qayta yuboradi.
"""
from __future__ import annotations

import logging
from typing import cast

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatMemberUpdated

from db.session import session_factory
from services.referral.tracked_chats import (
    TrackedChatType,
    deactivate_tracked_chat,
    upsert_tracked_chat,
)

logger = logging.getLogger(__name__)

router = Router(name="referral_admin_events")

# Bot chat a'zosi sifatida qaysi status'larda "faol" hisoblanadi.
_ACTIVE_STATUSES: frozenset[str] = frozenset(
    {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}
)
# Bu status'larda bot chatda emas.
_LEFT_STATUSES: frozenset[str] = frozenset(
    {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
)
_TRACKED_CHAT_TYPES: frozenset[str] = frozenset(
    {ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL}
)


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated) -> None:
    """Botning chatdagi statusi o'zgarganda ishga tushadi."""
    chat = event.chat
    if chat.type not in _TRACKED_CHAT_TYPES:
        # Private / undefined — bizga aloqasi yo'q.
        return

    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status
    logger.info(
        "my_chat_member: chat_id=%s type=%s %s -> %s",
        chat.id,
        chat.type,
        old_status,
        new_status,
    )

    try:
        async with session_factory() as session:
            if new_status in _LEFT_STATUSES:
                await deactivate_tracked_chat(
                    session,
                    chat_id=chat.id,
                    reason=f"bot_status={new_status}",
                )
                return

            if new_status == ChatMemberStatus.MEMBER:
                # Bot oddiy a'zo — invite link chiqarish uchun admin bo'lishi
                # kerak. Ro'yxatda mavjud bo'lsa nofaollashtiramiz.
                await deactivate_tracked_chat(
                    session,
                    chat_id=chat.id,
                    reason="bot_no_admin_rights",
                )
                return

            if new_status == ChatMemberStatus.RESTRICTED:
                await deactivate_tracked_chat(
                    session,
                    chat_id=chat.id,
                    reason="bot_restricted",
                )
                return

            if new_status not in _ACTIVE_STATUSES:
                # Kutilmagan status — xavfsizlik uchun log qilib chiqamiz.
                logger.warning(
                    "my_chat_member: kutilmagan status=%s chat_id=%s",
                    new_status,
                    chat.id,
                )
                return

            # Bot admin (yoki creator — bo'lishi ehtimoli past, lekin qamrab
            # olamiz). Invite link yarata olish huquqini tekshiramiz.
            new_member = event.new_chat_member
            can_invite = bool(getattr(new_member, "can_invite_users", False))
            if new_status == ChatMemberStatus.CREATOR:
                can_invite = True

            if not can_invite:
                logger.warning(
                    "TrackedChat chat_id=%s: bot admin, ammo can_invite_users=False. "
                    "is_active=False deb belgilanmoqda.",
                    chat.id,
                )

            await upsert_tracked_chat(
                session,
                chat_id=chat.id,
                title=chat.title or chat.full_name or str(chat.id),
                chat_type=cast(TrackedChatType, chat.type),
                username=chat.username,
                is_active=can_invite,
            )
    except Exception:  # noqa: BLE001
        # Telegram qayta urinmasin — xatoni yutamiz, lekin log qilamiz.
        logger.exception(
            "my_chat_member handler xatosi: chat_id=%s", chat.id
        )
