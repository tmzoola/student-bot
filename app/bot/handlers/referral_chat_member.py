"""T-018 · `chat_member` update handler — invite link joins tracking.

Telegram yangi a'zo chatga qo'shilganda / chatni tark etganda `chat_member`
update yuboradi (bu turdagi update `ALLOWED_UPDATES` da yoqilgan). Bu handler:

- JOIN: `old.status in {left, kicked}` va `new.status in {member, restricted}`
  bo'lganda + `update.invite_link` mavjud bo'lsa — `InviteJoin` yozadi va
  `InviteLink.join_count += 1`.
- LEAVE: `old.status in {member, restricted}` va `new.status in {left, kicked}`
  bo'lganda — aktiv `InviteJoin`'larni yopadi (`left_at`, `is_counted=False`,
  `join_count -= 1`).

Muhim: exception ko'tarilmasin — aks holda Telegram bir xil updateni qayta
yuborishi mumkin.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatMemberUpdated

from db.session import session_factory
from models.rewards import RewardTier
from services.referral.joins import JoinResult, record_join, record_leave

logger = logging.getLogger(__name__)

router = Router(name="referral_chat_member")

_TRACKED_CHAT_TYPES: frozenset[str] = frozenset(
    {ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL}
)
_PRESENT_STATUSES: frozenset[str] = frozenset(
    {ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED}
)
_ABSENT_STATUSES: frozenset[str] = frozenset(
    {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
)


@router.chat_member()
async def on_chat_member(event: ChatMemberUpdated) -> None:
    """Chatning oddiy a'zosi statusi o'zgarganda ishga tushadi."""
    chat = event.chat
    if chat.type not in _TRACKED_CHAT_TYPES:
        return

    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    user = event.new_chat_member.user
    if user is None or user.is_bot:
        # Botlar hisoblanmaydi.
        return

    is_join = old_status in _ABSENT_STATUSES and new_status in _PRESENT_STATUSES
    is_leave = (
        old_status in _PRESENT_STATUSES or old_status == ChatMemberStatus.ADMINISTRATOR
    ) and new_status in _ABSENT_STATUSES

    if not (is_join or is_leave):
        return

    logger.info(
        "chat_member: chat_id=%s tg=%s %s -> %s invite_link=%s",
        chat.id,
        user.id,
        old_status,
        new_status,
        getattr(event.invite_link, "invite_link", None),
    )

    result: JoinResult | None = None
    try:
        async with session_factory() as session:
            if is_join:
                invite_link_obj = event.invite_link
                if invite_link_obj is None or not invite_link_obj.invite_link:
                    # Foydalanuvchi boshqa yo'l bilan qo'shildi (masalan,
                    # public username, admin qo'shdi va h.k.).
                    return
                # Foydalanuvchi identity — admin panelda telegram_id'dan
                # tashqari username/ism-familiya bo'yicha ham topish uchun.
                full_name = (user.full_name or "").strip() or None
                username = user.username or None
                result = await record_join(
                    session,
                    tracked_chat_tg_id=chat.id,
                    joined_user_tg_id=user.id,
                    invite_link_str=invite_link_obj.invite_link,
                    joined_username=username,
                    joined_full_name=full_name,
                )
            else:  # is_leave
                await record_leave(
                    session,
                    tracked_chat_tg_id=chat.id,
                    left_user_tg_id=user.id,
                )
    except Exception:  # noqa: BLE001
        logger.exception(
            "chat_member handler xatosi: chat_id=%s tg=%s",
            chat.id,
            user.id,
        )
        return

    # T-021: yangi qozonilgan reward tier'lari uchun tabriknoma.
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
    """Foydalanuvchining shaxsiy chatiga tabriknoma yuboradi.

    Har qanday Telegram xatosi yutiladi — reward pipeline'i asosiy handler'ni
    yiqitmasligi kerak. Bot instance'i modul darajasida import qilinmaydi
    (circular import xavfi) — chaqiruv paytida import.
    """
    from bot.setup import bot  # local import — startup tsiklidan qochish uchun

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
