"""Admin tomonidan talaba arizasini tasdiqlash/rad etish."""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from core.config import settings
from db.session import session_factory
from models.faculty import Faculty
from models.student_profile import StudentProfile

logger = logging.getLogger(__name__)
router = Router(name="admin_approval")

_TZ = ZoneInfo("Asia/Tashkent")


def _approval_keyboard(profile_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve:{profile_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject:{profile_id}"),
            ]
        ]
    )


async def notify_admin_new_application(profile_id: int) -> None:
    """Yangi ariza haqida `ADMIN_CHAT_ID` ga xabar yuboradi.

    `ADMIN_CHAT_ID=0` bo'lsa faqat log yoziladi — bu dev muhitida normal.
    """
    if not settings.ADMIN_CHAT_ID:
        logger.warning(
            "ADMIN_CHAT_ID sozlanmagan — profile_id=%s uchun notify o'tkazib yuborildi",
            profile_id,
        )
        return
    async with session_factory() as session:
        profile = await session.scalar(
            select(StudentProfile)
            .options(selectinload(StudentProfile.faculty), selectinload(StudentProfile.telegram_user))
            .where(StudentProfile.id == profile_id)
        )
    if profile is None:
        logger.error("notify_admin: profile %s topilmadi", profile_id)
        return
    text = (
        "🆕 Yangi ariza\n\n"
        f"👤 <b>{profile.full_name}</b>\n"
        f"🆔 ID: <code>{profile.student_id_number}</code>\n"
        f"🏛 Fakultet: {profile.faculty.name if profile.faculty else '—'}\n"
        f"📚 Kurs: {profile.course_number} · Semestr: {profile.semester}\n"
        f"📨 Telegram: @{profile.telegram_user.username or '—'} "
        f"(<code>{profile.telegram_user.telegram_id}</code>)"
    )
    from bot.setup import bot

    try:
        await bot.send_message(
            settings.ADMIN_CHAT_ID,
            text,
            reply_markup=_approval_keyboard(profile.id),
        )
    except Exception:  # noqa: BLE001
        logger.exception("adminga xabar yuborishda xato (chat_id=%s)", settings.ADMIN_CHAT_ID)


def _is_admin_source(cb: CallbackQuery) -> bool:
    if not settings.ADMIN_CHAT_ID:
        return False
    if cb.message is None or cb.message.chat is None:
        return False
    return cb.message.chat.id == settings.ADMIN_CHAT_ID


@router.callback_query(F.data.startswith("approve:"))
async def on_approve(cb: CallbackQuery) -> None:
    if not _is_admin_source(cb):
        await cb.answer("Ruxsat yo'q", show_alert=True)
        return
    profile_id = int(cb.data.split(":", 1)[1])
    async with session_factory() as session:
        profile = await session.scalar(
            select(StudentProfile).where(StudentProfile.id == profile_id)
        )
        if profile is None:
            await cb.answer("Ariza topilmadi (ehtimol allaqachon rad etilgan)", show_alert=True)
            return
        if profile.is_approved:
            await cb.answer("Allaqachon tasdiqlangan", show_alert=True)
            return
        profile.is_approved = True
        profile.approved_at = datetime.now(_TZ)
        profile.approved_by = cb.from_user.id
        await session.commit()
        await session.refresh(profile, attribute_names=["telegram_user"])
        telegram_id = profile.telegram_user.telegram_id

    await cb.message.edit_text(
        (cb.message.text or "") + "\n\n✅ Tasdiqlandi",
        reply_markup=None,
    )
    await cb.answer("Tasdiqlandi")

    from bot.handlers.menu import send_main_menu_by_id
    from bot.setup import bot

    try:
        await bot.send_message(telegram_id, "🎉 Arizangiz tasdiqlandi! Botdan foydalanishingiz mumkin.")
        await send_main_menu_by_id(telegram_id)
    except Exception:  # noqa: BLE001
        logger.exception("approve: foydalanuvchiga xabar yuborilmadi (%s)", telegram_id)


@router.callback_query(F.data.startswith("reject:"))
async def on_reject(cb: CallbackQuery) -> None:
    if not _is_admin_source(cb):
        await cb.answer("Ruxsat yo'q", show_alert=True)
        return
    profile_id = int(cb.data.split(":", 1)[1])
    async with session_factory() as session:
        profile = await session.scalar(
            select(StudentProfile)
            .options(selectinload(StudentProfile.telegram_user))
            .where(StudentProfile.id == profile_id)
        )
        if profile is None:
            await cb.answer("Ariza topilmadi", show_alert=True)
            return
        telegram_id = profile.telegram_user.telegram_id
        await session.execute(delete(StudentProfile).where(StudentProfile.id == profile_id))
        await session.commit()

    await cb.message.edit_text(
        (cb.message.text or "") + "\n\n❌ Rad etildi",
        reply_markup=None,
    )
    await cb.answer("Rad etildi")

    from bot.setup import bot

    try:
        await bot.send_message(
            telegram_id,
            "Kechirasiz, arizangiz rad etildi. Ma'lumotlaringizni tekshirib, qayta yuborishingiz mumkin — /start bosing.",
        )
    except Exception:  # noqa: BLE001
        logger.exception("reject: foydalanuvchiga xabar yuborilmadi (%s)", telegram_id)


# Faculty lazy import xatoni oldini olish uchun.
_ = Faculty
