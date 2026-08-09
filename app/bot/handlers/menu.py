"""Tasdiqlangan talaba uchun asosiy menyu."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from core.config import settings
from db.session import session_factory
from models.attempt import QuizAttempt
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)
router = Router(name="menu")


BTN_SUBJECTS = "📚 Fanlar"
BTN_PROFILE = "👤 Profil"
BTN_STATS = "📊 Statistika"


def _main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SUBJECTS, web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/subjects"))],
            [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_STATS)],
        ],
        resize_keyboard=True,
    )


def _inline_webapp_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Fanlarni ochish",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/subjects"),
                )
            ]
        ]
    )


async def send_main_menu(msg: Message, profile: StudentProfile) -> None:
    await msg.answer(
        f"Assalomu alaykum, <b>{profile.full_name}</b>! Nima qilamiz?",
        reply_markup=_main_kb(),
    )
    await msg.answer(
        "Yoki quyidagi tugma orqali oching:",
        reply_markup=_inline_webapp_kb(),
    )


async def send_main_menu_by_id(telegram_id: int) -> None:
    from bot.setup import bot

    await bot.send_message(
        telegram_id,
        "Asosiy menyu:",
        reply_markup=_main_kb(),
    )
    await bot.send_message(
        telegram_id,
        "Yoki quyidagi tugma orqali oching:",
        reply_markup=_inline_webapp_kb(),
    )


async def _load_profile_by_tg(telegram_id: int) -> StudentProfile | None:
    async with session_factory() as session:
        return await session.scalar(
            select(StudentProfile)
            .options(selectinload(StudentProfile.faculty), selectinload(StudentProfile.telegram_user))
            .join(TelegramUser, TelegramUser.id == StudentProfile.telegram_user_id)
            .where(TelegramUser.telegram_id == telegram_id)
        )


@router.message(F.text == BTN_PROFILE)
async def on_profile(msg: Message) -> None:
    profile = await _load_profile_by_tg(msg.from_user.id)
    if profile is None or not profile.is_approved:
        return
    await msg.answer(
        f"👤 <b>{profile.full_name}</b>\n"
        f"🆔 {profile.student_id_number}\n"
        f"🏛 Fakultet: {profile.faculty.name if profile.faculty else '—'}\n"
        f"📚 Kurs: {profile.course_number} · Semestr: {profile.semester}",
    )


@router.message(F.text == BTN_STATS)
async def on_stats(msg: Message) -> None:
    profile = await _load_profile_by_tg(msg.from_user.id)
    if profile is None or not profile.is_approved:
        return
    async with session_factory() as session:
        row = (
            await session.execute(
                select(
                    func.count(QuizAttempt.id),
                    func.coalesce(func.sum(QuizAttempt.score), 0),
                    func.coalesce(func.sum(QuizAttempt.total), 0),
                ).where(QuizAttempt.student_profile_id == profile.id)
            )
        ).one()
    attempts, total_score, total_max = int(row[0]), int(row[1]), int(row[2])
    avg = round(total_score / total_max * 100) if total_max else 0
    await msg.answer(
        "📊 <b>Statistika</b>\n\n"
        f"Urinishlar: <b>{attempts}</b>\n"
        f"Umumiy ball: <b>{total_score}</b> / {total_max}\n"
        f"O'rtacha foiz: <b>{avg}%</b>",
    )
