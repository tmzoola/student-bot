"""T-017 · "🔗 Taklif linki" reply tugmasi va chat tanlash inline flow.

Flow:
  1. Foydalanuvchi "🔗 Taklif linki" ni bosadi.
  2. Bot faol TrackedChat'lar ro'yxatini inline keyboard sifatida ko'rsatadi.
  3. Foydalanuvchi chatni tanlaydi → shaxsiy invite link yuboriladi.

Xatoliklar (nofaol chat, ruxsat yo'q, rate-limit) o'zbek tilida ko'rsatiladi.
"""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from core.exceptions import AppException
from db.session import session_factory
from models.referral import TrackedChat
from models.telegram_user import TelegramUser
from services.referral.invite_links import get_or_create_invite_link

logger = logging.getLogger(__name__)

router = Router(name="referral_menu")

_BTN_LABEL = "🔗 Taklif linki"
_CB_PREFIX = "referral:chat:"


def _chats_keyboard(chats: list[TrackedChat]) -> InlineKeyboardMarkup:
    """Faol chatlar ro'yxatidan inline keyboard yasaydi."""
    rows = [
        [InlineKeyboardButton(
            text=f"📢 {chat.title}",
            callback_data=f"{_CB_PREFIX}{chat.id}",
        )]
        for chat in chats
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_active_chats() -> list[TrackedChat]:
    async with session_factory() as session:
        result = await session.execute(
            select(TrackedChat)
            .where(TrackedChat.is_active == True)  # noqa: E712
            .order_by(TrackedChat.id)
        )
        return list(result.scalars().all())


async def _get_user_by_tg_id(tg_id: int) -> TelegramUser | None:
    async with session_factory() as session:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == tg_id)
        )
        return result.scalar_one_or_none()


@router.message(F.text == _BTN_LABEL)
async def referral_link_menu(msg: Message) -> None:
    """Foydalanuvchi "🔗 Taklif linki" tugmasini bosganda chaqiriladi."""
    chats = await _get_active_chats()
    if not chats:
        await msg.answer(
            "🔗 <b>Taklif linki</b>\n\n"
            "Hozircha hech qanday kanal mavjud emas.\n"
            "Tez orada yangi kanallar qo'shiladi! 🔔"
        )
        return

    await msg.answer(
        "🔗 <b>Taklif linki</b>\n\n"
        "Do'stlaringizni qaysi kanalga taklif qilmoqchisiz?\n"
        "Quyidan kanallardan birini tanlang 👇",
        reply_markup=_chats_keyboard(chats),
    )


@router.callback_query(F.data.startswith(_CB_PREFIX))
async def referral_chat_selected(cb: CallbackQuery, bot: Bot) -> None:
    """Foydalanuvchi kanaldan birini tanlaganda shaxsiy invite link yuboriladi."""
    await cb.answer()

    raw_id = cb.data[len(_CB_PREFIX):]
    if not raw_id.isdigit():
        await cb.message.answer("❌ Noto'g'ri so'rov. Iltimos, qaytadan urinib ko'ring.")
        return

    tracked_chat_id = int(raw_id)
    tg_user = cb.from_user

    user = await _get_user_by_tg_id(tg_user.id)
    if user is None:
        await cb.message.answer(
            "❌ Siz hali ro'yxatdan o'tmagansiz.\n"
            "Ro'yxatdan o'tish uchun /start bosing."
        )
        return

    try:
        async with session_factory() as session:
            # tracked_chat ma'lumotini avval olamiz — title uchun kerak
            tracked = await session.get(TrackedChat, tracked_chat_id)
            chat_title = tracked.title if tracked else "Kanal"

            invite = await get_or_create_invite_link(
                session,
                bot,
                user_id=user.id,
                tracked_chat_id=tracked_chat_id,
            )
            join_count = invite.join_count
            link_url = invite.invite_link
    except AppException as exc:
        await cb.message.answer(f"⚠️ {exc.detail}")
        return
    except Exception:
        logger.exception(
            "referral_chat_selected: kutilmagan xato user_id=%s tracked_chat_id=%s",
            tg_user.id,
            tracked_chat_id,
        )
        await cb.message.answer(
            "❌ Kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )
        return

    await cb.message.answer(
        f"🔗 <b>{chat_title}</b> uchun shaxsiy taklif linkingiz:\n\n"
        f"<code>{link_url}</code>\n\n"
        f"👥 Hozirgacha taklif qilinganlar: <b>{join_count}</b>\n\n"
        "👆 Yuqoridagi linkni nusxalab do'stlaringizga yuboring!\n"
        "Har bir do'stingiz shu link orqali kanalga qo'shilsa hisoblanadi. 🎯",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📤 Do'stlarga ulashish",
                switch_inline_query=link_url,
            ),
        ]]),
    )
