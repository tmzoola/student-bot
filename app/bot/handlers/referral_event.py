"""Referral konkurs "✅ Obuna bo'ldim" / "🔄 Yangilash" callback flow.

`/start` faol event bo'lsa e'lon + "Obuna bo'ldim" tugmasini yuboradi
(`bot/router.py`). Bu handler tugma bosilganda:
  1. Foydalanuvchi barcha faol tracked chatlarga a'zomi — tekshiradi.
  2. A'zo bo'lmasa: yetishmayotgan chatlar + qo'shilish tugmalarini ko'rsatadi.
  3. Barchasiga a'zo bo'lsa: ishtirokchi raqamini beradi, har bir chat uchun
     shaxsiy invite link generatsiya qiladi va chipta xabarini yuboradi.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import select

from core.config import settings
from core.exceptions import AppException
from db.session import session_factory
from models.referral import TrackedChat
from models.telegram_user import TelegramUser
from services.referral.events import (
    REFRESH_CB,
    SUBSCRIBED_CB,
    chat_join_url,
    count_referral_on_gate,
    get_active_event,
    get_or_create_participant,
    normalize_newlines,
    referral_deeplink,
    referral_ticket_count,
    share_button,
)
from services.referral.membership import check_subscription

logger = logging.getLogger(__name__)

router = Router(name="referral_event")

_TZ = ZoneInfo("Asia/Tashkent")


def _missing_keyboard(chats: list[TrackedChat]) -> InlineKeyboardMarkup:
    """Yetishmayotgan chatlar uchun qo'shilish + qayta tekshirish tugmalari."""
    rows: list[list[InlineKeyboardButton]] = []
    for chat in chats:
        url = chat_join_url(chat)
        if url is None:
            continue
        icon = "📢" if chat.type == "channel" else "👥"
        rows.append([InlineKeyboardButton(text=f"{icon} {chat.title}", url=url)])
    rows.append(
        [InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data=SUBSCRIBED_CB)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _get_user(tg_id: int) -> TelegramUser | None:
    async with session_factory() as session:
        return (
            await session.execute(
                select(TelegramUser).where(TelegramUser.telegram_id == tg_id)
            )
        ).scalar_one_or_none()


@router.callback_query(F.data.in_({SUBSCRIBED_CB, REFRESH_CB}))
async def on_subscribed(cb: CallbackQuery, bot: Bot) -> None:
    """"Obuna bo'ldim" / "Yangilash" bosilganda a'zolikni tekshiradi.

    FAQAT shaxsiy chatda ishlaydi — guruh/kanalда bosilsa bot u yerga xabar
    yozmasin (aks holda guruhga spam bo'ladi).
    """
    # Guruh/supergruh/kanalда — javobni faqat ephemeral alert sifatida beramiz.
    if cb.message is None or cb.message.chat.type != "private":
        await cb.answer(
            f"Iltimos, botni shaxsiy chatda oching: @{settings.BOT_USERNAME}",
            show_alert=True,
        )
        return

    await cb.answer()

    now = datetime.now(_TZ)
    async with session_factory() as session:
        event = await get_active_event(session, now)
    if event is None:
        await cb.message.answer(
            "⏳ Konkurs hozircha faol emas. Iltimos, keyinroq urinib ko'ring."
        )
        return

    user = await _get_user(cb.from_user.id)
    if user is None:
        await cb.message.answer(
            "❌ Siz hali ro'yxatdan o'tmagansiz.\n"
            "Ro'yxatdan o'tish uchun /start bosing."
        )
        return

    async with session_factory() as session:
        ok, missing = await check_subscription(
            session, bot, user_tg_id=cb.from_user.id
        )

    if not ok:
        missing_lines = "\n".join(
            f"{'📢' if c.type == 'channel' else '👥'} {c.title}" for c in missing
        )
        await cb.message.answer(
            "👀 Hali sizni quyidagilarda ko'rmayapman:\n\n"
            f"{missing_lines}\n\n"
            "Obuna bo'ling va yana <b>«✅ Obuna bo'ldim»</b> tugmasini bosing:",
            reply_markup=_missing_keyboard(missing),
        )
        return

    # Barcha chatlarga a'zo — ishtirokchi raqami + shaxsiy deep-link.
    try:
        async with session_factory() as session:
            participant = await get_or_create_participant(
                session, event_id=event.id, user_id=user.id
            )
            number = participant.number

            # Obuna gate'dan o'tdi — bizni taklif qilgan bo'lsa unga chipta.
            await count_referral_on_gate(
                session,
                event_id=event.id,
                invited_tg_id=cb.from_user.id,
                invited_user_id=user.id,
            )

            tickets = await referral_ticket_count(
                session, event_id=event.id, inviter_user_id=user.id
            )
    except AppException as exc:
        await cb.message.answer(f"⚠️ {exc.detail}")
        return
    except Exception:
        logger.exception(
            "referral_event: kutilmagan xato user=%s event=%s",
            cb.from_user.id,
            event.id,
        )
        await cb.message.answer(
            "❌ Kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )
        return

    deeplink = referral_deeplink(cb.from_user.id)
    await cb.message.answer(
        _ticket_text(event, number=number, tickets=tickets, deeplink=deeplink),
        reply_markup=_ticket_keyboard(
            cb.from_user.id, event.share_text or event.announcement_text
        ),
        disable_web_page_preview=True,
    )


def _ticket_text(
    event,
    *,
    number: int,
    tickets: int,
    deeplink: str,
) -> str:
    header = normalize_newlines(event.success_text) or (
        "🎉 <b>Tabriklaymiz! Siz konkursda ishtirok etyapsiz!</b>"
    )
    return "\n".join([
        header,
        "",
        f"👤 Ishtirokchi <b>№{number}</b> · Chiptalaringiz: <b>{tickets}</b>",
        "",
        "🔗 <b>Sizning shaxsiy taklif havolangiz:</b>",
        deeplink,
        "",
        "Hurmatli ustoz, ushbu havolani boshqa ustozlar bilan ulashing va "
        "ularni ushbu tanlovda ishtirok etishga taklif qiling. 🤝",
        "",
        "Birgalikda bilim va tajribamizni bo'lishaylik — har bir taklif qilingan "
        "ishtirokchi g'alaba imkoniyatingizni oshiradi! 🌟",
    ])


def _ticket_keyboard(
    inviter_tg_id: int, announcement_text: str | None
) -> InlineKeyboardMarkup:
    # `t.me/share/url` orqali ulashish — inline mode talab qilmaydi, do'stga
    # to'liq promo matn + shaxsiy deep-link yuboriladi.
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [share_button(inviter_tg_id, announcement_text)],
            [
                InlineKeyboardButton(
                    text="🔄 Chiptalarni yangilash", callback_data=REFRESH_CB
                )
            ],
        ]
    )
