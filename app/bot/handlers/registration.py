"""Talaba ro'yxatdan o'tish FSM.

Yangi foydalanuvchi `/start` bosgan zahoti (StudentProfile mavjud bo'lmasa)
quyidagi ketma-ketlik boshlanadi:
  student_id -> full_name -> faculty -> course -> semester -> submit
Yakunda `StudentProfile(is_approved=False)` yaratiladi va adminga xabar
yuboriladi (T-202).
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from bot.router import get_or_create_user
from db.session import session_factory
from models.faculty import Faculty
from models.student_profile import StudentProfile

logger = logging.getLogger(__name__)
router = Router(name="registration")


class Registration(StatesGroup):
    waiting_student_id = State()
    waiting_full_name = State()
    waiting_faculty = State()
    waiting_course = State()
    waiting_semester = State()


async def _get_profile(telegram_user_id: int) -> StudentProfile | None:
    async with session_factory() as session:
        return await session.scalar(
            select(StudentProfile).where(
                StudentProfile.telegram_user_id == telegram_user_id
            )
        )


async def _faculties_keyboard() -> InlineKeyboardMarkup | None:
    async with session_factory() as session:
        rows = (
            await session.scalars(
                select(Faculty).where(Faculty.is_active.is_(True)).order_by(Faculty.name)
            )
        ).all()
    if not rows:
        return None
    buttons = [
        [InlineKeyboardButton(text=f.name, callback_data=f"reg_fac:{f.id}")]
        for f in rows
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _course_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=f"{n}-kurs", callback_data=f"reg_course:{n}")
        for n in range(1, 5)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


def _semester_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=f"{n}-semestr", callback_data=f"reg_sem:{n}")
        for n in (1, 2)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext) -> None:
    user = await get_or_create_user(msg.from_user)
    profile = await _get_profile(user.id)
    if profile is None:
        await state.clear()
        await state.set_state(Registration.waiting_student_id)
        await msg.answer(
            "Assalomu alaykum! Student-bot roʻyxatdan oʻtish uchun sizdan bir nechta maʼlumot soʻraydi.\n\n"
            "1) Talabalik ID raqamingizni yuboring (masalan, `2023-CS-0001`):",
        )
        return
    if not profile.is_approved:
        await msg.answer(
            "Arizangiz admin tomonidan koʻrib chiqilmoqda. Iltimos, kuting."
        )
        return
    # Tasdiqlangan foydalanuvchi — asosiy menyu (T-203) chaqiriladi.
    from bot.handlers.menu import send_main_menu

    await send_main_menu(msg, profile)


@router.message(Registration.waiting_student_id, F.text)
async def on_student_id(msg: Message, state: FSMContext) -> None:
    student_id = (msg.text or "").strip()
    if len(student_id) < 3 or len(student_id) > 64:
        await msg.answer("ID juda qisqa yoki uzun. Qaytadan kiriting:")
        return
    async with session_factory() as session:
        exists = await session.scalar(
            select(StudentProfile.id).where(
                StudentProfile.student_id_number == student_id
            )
        )
    if exists:
        await msg.answer("Bu ID allaqachon ishlatilgan. Boshqa ID kiriting:")
        return
    await state.update_data(student_id=student_id)
    await state.set_state(Registration.waiting_full_name)
    await msg.answer("2) Toʻliq ismingizni yuboring (F.I.Sh):")


@router.message(Registration.waiting_full_name, F.text)
async def on_full_name(msg: Message, state: FSMContext) -> None:
    full_name = (msg.text or "").strip()
    if len(full_name) < 3 or len(full_name) > 255:
        await msg.answer("Ism juda qisqa. Qaytadan kiriting:")
        return
    await state.update_data(full_name=full_name)
    kb = await _faculties_keyboard()
    if kb is None:
        await msg.answer(
            "Fakultetlar hali sozlanmagan. Iltimos, admin sozlagach qayta urining."
        )
        await state.clear()
        return
    await state.set_state(Registration.waiting_faculty)
    await msg.answer("3) Fakultetingizni tanlang:", reply_markup=kb)


@router.callback_query(Registration.waiting_faculty, F.data.startswith("reg_fac:"))
async def on_faculty(cb: CallbackQuery, state: FSMContext) -> None:
    faculty_id = int(cb.data.split(":", 1)[1])
    await state.update_data(faculty_id=faculty_id)
    await state.set_state(Registration.waiting_course)
    await cb.message.edit_text("4) Kursingizni tanlang:", reply_markup=_course_keyboard())
    await cb.answer()


@router.callback_query(Registration.waiting_course, F.data.startswith("reg_course:"))
async def on_course(cb: CallbackQuery, state: FSMContext) -> None:
    course = int(cb.data.split(":", 1)[1])
    if course not in (1, 2, 3, 4):
        await cb.answer("Notoʻgʻri qiymat", show_alert=True)
        return
    await state.update_data(course_number=course)
    await state.set_state(Registration.waiting_semester)
    await cb.message.edit_text("5) Semestrni tanlang:", reply_markup=_semester_keyboard())
    await cb.answer()


@router.callback_query(Registration.waiting_semester, F.data.startswith("reg_sem:"))
async def on_semester(cb: CallbackQuery, state: FSMContext) -> None:
    semester = int(cb.data.split(":", 1)[1])
    if semester not in (1, 2):
        await cb.answer("Notoʻgʻri qiymat", show_alert=True)
        return
    data = await state.get_data()
    data["semester"] = semester

    user = await get_or_create_user(cb.from_user)
    profile = await _create_profile(user.id, data)
    await state.clear()

    await cb.message.edit_text(
        "Arizangiz qabul qilindi. Admin tasdiqlashini kuting — tez orada javob keladi."
    )
    await cb.answer("Yuborildi")

    # Adminga xabar yuborish alohida modulda (T-202).
    try:
        from bot.handlers.admin_approval import notify_admin_new_application

        await notify_admin_new_application(profile.id)
    except Exception:  # noqa: BLE001
        logger.exception("admin notify failed for profile %s", profile.id)


async def _create_profile(telegram_user_id: int, data: dict) -> StudentProfile:
    async with session_factory() as session:
        profile = StudentProfile(
            telegram_user_id=telegram_user_id,
            student_id_number=data["student_id"],
            full_name=data["full_name"],
            faculty_id=data["faculty_id"],
            course_number=data["course_number"],
            semester=data["semester"],
            is_approved=False,
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return profile


@router.message(StateFilter(Registration), ~F.text)
async def on_bad_input(msg: Message) -> None:
    await msg.answer("Iltimos, matn koʻrinishida javob yuboring.")
