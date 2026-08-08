"""Inline query handler — "📤 Do'stlarga ulashish" tugmasi uchun.

Foydalanuvchi Telegram inline mode'ga o'tganda (bizning "Do'stlarga ulashish"
tugmasi orqali) bu handler bitta natija qaytaradi: konkurs e'loni matni +
rasm + ikkita inline tugma:

    🎁 Qatnashaman — botga /start ref_<inviter_id> deep-link
    📤 Do'stlarga ulashish — inline mode'ni qayta ochish

Natijani tanlagach, Telegram uni tanlangan chatga xabar sifatida yuboradi.
BotFather'da bot uchun inline mode yoqilgan bo'lishi shart.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
)

from sqlalchemy import select

from core.config import settings
from db.session import session_factory
from models.telegram_user import TelegramUser
from services.referral.events import (
    get_active_event,
    get_active_tracked_chats,
    referral_deeplink,
)
from services.referral.invite_links import get_or_create_invite_link

logger = logging.getLogger(__name__)

router = Router(name="referral_inline")

_TZ = ZoneInfo("Asia/Tashkent")


def _share_keyboard(inviter_id: int) -> InlineKeyboardMarkup:
    start_url = f"https://t.me/{settings.BOT_USERNAME}?start=ref_{inviter_id}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Qatnashaman", url=start_url)],
            [InlineKeyboardButton(
                text="📤 Do'stlar va guruhlarga ulashish",
                switch_inline_query="",
            )],
        ]
    )


def _resolve_photo_url(image_url: str | None) -> str | None:
    """Inline result uchun rasmga to'liq HTTPS URL qaytaradi (yoki None)."""
    if not image_url:
        return None
    if image_url.startswith(("http://", "https://")):
        return image_url
    # Media ichidagi lokal fayl — WEBAPP_URL orqali xizmat qiladi.
    base = settings.WEBAPP_URL.rstrip("/")
    return f"{base}/media/{image_url.lstrip('/')}"


async def _build_caption(session, bot, event, inviter_tg_id: int) -> str:
    """E'lon matni + inviter shaxsiy deep-link havolasi + CTA (har doim to'la)."""
    base = (event.announcement_text or "🎉 Konkursda ishtirok eting!").strip()
    deeplink = referral_deeplink(inviter_tg_id)

    parts = [
        base,
        "",
        "🔗 <b>Shaxsiy taklif havolangiz:</b>",
        deeplink,
    ]

    user = (
        await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == inviter_tg_id)
        )
    ).scalar_one_or_none()
    if user is not None:
        chan_lines: list[str] = []
        for chat in await get_active_tracked_chats(session):
            try:
                link = await get_or_create_invite_link(
                    session, bot, user_id=user.id, tracked_chat_id=chat.id
                )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "inline: invite link olib bo'lmadi chat=%s user=%s",
                    chat.id, user.id,
                )
                continue
            icon = "📢" if chat.type == "channel" else "👥"
            chan_lines.append(f"{icon} <b>{chat.title}</b>:\n{link.invite_link}")
        if chan_lines:
            parts.append("")
            parts.append("📌 Kanal/guruhlar:")
            parts.extend(chan_lines)

    parts += [
        "",
        "🎁 Konkursda ishtirok eting va qimmatbaho sovg'alarni yutib oling! 🏆",
    ]
    return "\n".join(parts)


@router.inline_query()
async def on_inline_query(query: InlineQuery) -> None:
    from bot.setup import bot as _bot

    inviter = query.from_user
    now = datetime.now(_TZ)

    async with session_factory() as session:
        event = await get_active_event(session, now)
        if event is None:
            await query.answer(results=[], cache_time=5, is_personal=True)
            return
        try:
            text = await _build_caption(session, _bot, event, inviter.id)
            await session.commit()
        except Exception:  # noqa: BLE001
            logger.exception("inline caption qurishda xato: inviter=%s", inviter.id)
            text = event.announcement_text or "🎉 Konkursda ishtirok eting!"

    kb = _share_keyboard(inviter.id)
    photo_url = _resolve_photo_url(event.image_url)
    # Telegram: rasm captioni max ~1024 belgi. Cheklab qo'yamiz.
    if len(text) > 1000:
        text = text[:1000].rstrip() + "…"

    results: list = []
    if photo_url:
        results.append(
            InlineQueryResultPhoto(
                id=str(uuid4()),
                photo_url=photo_url,
                thumbnail_url=photo_url,
                title="Konkursda qatnashish",
                description=text[:120],
                caption=text,
                parse_mode="HTML",
                reply_markup=kb,
            )
        )
    else:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Konkursda qatnashish",
                description=text[:120],
                input_message_content=InputTextMessageContent(
                    message_text=text,
                    parse_mode="HTML",
                ),
                reply_markup=kb,
            )
        )

    try:
        await query.answer(results=results, cache_time=0, is_personal=True)
    except Exception:  # noqa: BLE001
        logger.exception("inline_query javobida xato: inviter=%s", inviter.id)
