"""Kanal (va "join request" yoqilgan guruh) uchun taklif kuzatuvi.

Telegram Bot API `chat_member` update'ini kanallarda yubormaydi — shu sababli
kanal uchun invite link kuzatuvi `chat_join_request` orqali qilinadi. Kanal
sozlamalarida "Approve New Members" (join requests) yoqilishi shart. Bot admin
bo'lganda va invite link "join request" rejimida bo'lganda, foydalanuvchi
qo'shilishga so'rov yuborsa, Telegram bizga `chat_join_request` update yuboradi
— shu paytda link egasini aniqlab, `record_join` chaqirib, so'rovni avto
tasdiqlaymiz.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.types import ChatJoinRequest

from db.session import session_factory
from models.rewards import RewardTier
from services.referral.joins import record_join

logger = logging.getLogger(__name__)

router = Router(name="referral_join_request")

_TRACKED_CHAT_TYPES: frozenset[str] = frozenset(
    {ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL}
)


@router.chat_join_request()
async def on_chat_join_request(event: ChatJoinRequest) -> None:
    chat = event.chat
    user = event.from_user
    if chat.type not in _TRACKED_CHAT_TYPES or user is None or user.is_bot:
        return

    invite = event.invite_link
    invite_link_str = getattr(invite, "invite_link", None) if invite else None

    logger.info(
        "chat_join_request: chat_id=%s type=%s tg=%s invite_link=%s",
        chat.id,
        chat.type,
        user.id,
        invite_link_str,
    )

    result = None
    if invite_link_str:
        full_name = (user.full_name or "").strip() or None
        username = user.username or None
        try:
            async with session_factory() as session:
                result = await record_join(
                    session,
                    tracked_chat_tg_id=chat.id,
                    joined_user_tg_id=user.id,
                    invite_link_str=invite_link_str,
                    joined_username=username,
                    joined_full_name=full_name,
                )
        except Exception:  # noqa: BLE001
            logger.exception(
                "chat_join_request record_join xatosi: chat_id=%s tg=%s",
                chat.id,
                user.id,
            )

    # Har qanday holatda so'rovni tasdiqlaymiz — foydalanuvchi kutmasin.
    from bot.setup import bot  # local import — circular importdan qochish

    try:
        await bot.approve_chat_join_request(chat.id, user.id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "approve_chat_join_request xatosi: chat_id=%s tg=%s",
            chat.id,
            user.id,
        )

    if (
        result is not None
        and result.counted
        and result.newly_earned_rewards
        and result.inviter_tg_id is not None
    ):
        await _notify_rewards(
            inviter_tg_id=result.inviter_tg_id,
            rewards=result.newly_earned_rewards,
        )


async def _notify_rewards(
    *, inviter_tg_id: int, rewards: list[RewardTier]
) -> None:
    from bot.setup import bot

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
                "reward tabriknoma yuborilmadi: tg=%s tier_id=%s",
                inviter_tg_id,
                tier.id,
            )
