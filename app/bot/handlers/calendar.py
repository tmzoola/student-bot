"""📅 Kalendar — talaba deadlinelari va shaxsiy eslatmalar."""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from db.session import session_factory
from models.deadline import Deadline, PersonalDeadline
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)
router = Router(name="calendar")

_TZ = ZoneInfo("Asia/Tashkent")

BTN_CALENDAR = "📅 Kalendar"


class AddDeadlineFSM(StatesGroup):
    waiting_title = State()
    waiting_date = State()


# ── helpers ──────────────────────────────────────────────────────────────────

async def _get_profile(telegram_id: int) -> StudentProfile | None:
    async with session_factory() as session:
        return await session.scalar(
            select(StudentProfile)
            .join(TelegramUser, TelegramUser.id == StudentProfile.telegram_user_id)
            .where(
                TelegramUser.telegram_id == telegram_id,
                StudentProfile.is_approved.is_(True),
            )
        )


def _fmt_dt(dt: datetime) -> str:
    return dt.astimezone(_TZ).strftime("%d.%m.%Y %H:%M")


def _time_left(dt: datetime) -> str:
    now = datetime.now(_TZ)
    diff = dt.astimezone(_TZ) - now
    if diff.total_seconds() <= 0:
        return "⛔ Muddati o'tdi"
    days = diff.days
    hours, rem = divmod(diff.seconds, 3600)
    if days > 0:
        return f"⏳ {days} kun {hours} soat qoldi"
    return f"⏳ {hours} soat {rem // 60} daqiqa qoldi"


# ── main calendar view ────────────────────────────────────────────────────────

@router.message(F.text == BTN_CALENDAR)
async def on_calendar(msg: Message) -> None:
    profile = await _get_profile(msg.from_user.id)
    if profile is None:
        return

    async with session_factory() as session:
        now = datetime.now(_TZ)

        admin_deadlines = (await session.scalars(
            select(Deadline)
            .where(
                Deadline.is_active.is_(True),
                Deadline.deadline_at >= now,
            )
            .where(
                (Deadline.faculty_id == None) | (Deadline.faculty_id == profile.faculty_id)  # noqa: E711
            )
            .order_by(Deadline.deadline_at)
            .limit(10)
        )).all()

        personal = (await session.scalars(
            select(PersonalDeadline)
            .where(
                PersonalDeadline.student_profile_id == profile.id,
                PersonalDeadline.deadline_at >= now,
            )
            .order_by(PersonalDeadline.deadline_at)
            .limit(10)
        )).all()

    lines = ["📅 <b>Deadlinelar</b>\n"]

    if admin_deadlines:
        lines.append("🏛 <b>Universitet deadlinelari:</b>")
        for d in admin_deadlines:
            lines.append(
                f"  • <b>{d.title}</b>\n"
                f"    🗓 {_fmt_dt(d.deadline_at)}\n"
                f"    {_time_left(d.deadline_at)}"
            )
    else:
        lines.append("🏛 Hozircha aktiv deadline yo'q.")

    lines.append("")

    if personal:
        lines.append("📝 <b>Shaxsiy eslatmalarim:</b>")
        for p in personal:
            lines.append(
                f"  • <b>{p.title}</b>\n"
                f"    🗓 {_fmt_dt(p.deadline_at)}\n"
                f"    {_time_left(p.deadline_at)}"
            )
    else:
        lines.append("📝 Shaxsiy eslatmalar yo'q.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Eslatma qo'shish", callback_data="add_personal_deadline")],
    ])
    await msg.answer("\n".join(lines), reply_markup=kb)


# ── add personal deadline FSM ─────────────────────────────────────────────────

@router.callback_query(F.data == "add_personal_deadline")
async def on_add_deadline_start(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.set_state(AddDeadlineFSM.waiting_title)
    await cb.message.answer(
        "📝 Eslatma sarlavhasini yozing:\n"
        "<i>(Masalan: Kurs ishi topshirish)</i>"
    )


@router.message(AddDeadlineFSM.waiting_title)
async def on_deadline_title(msg: Message, state: FSMContext) -> None:
    title = msg.text.strip()
    if len(title) < 2 or len(title) > 255:
        await msg.answer("❌ Sarlavha 2–255 belgi bo'lishi kerak.")
        return
    await state.update_data(title=title)
    await state.set_state(AddDeadlineFSM.waiting_date)
    await msg.answer(
        "📅 Muddat sanasini kiriting:\n"
        "<code>KK.OO.YYYY SS:MM</code> formatida\n\n"
        "<i>Masalan: 25.08.2026 14:00</i>"
    )


@router.message(AddDeadlineFSM.waiting_date)
async def on_deadline_date(msg: Message, state: FSMContext) -> None:
    raw = msg.text.strip()
    try:
        naive = datetime.strptime(raw, "%d.%m.%Y %H:%M")
        dt = naive.replace(tzinfo=_TZ)
    except ValueError:
        await msg.answer(
            "❌ Format noto'g'ri. Iltimos quyidagicha kiriting:\n"
            "<code>KK.OO.YYYY SS:MM</code>\n"
            "<i>Masalan: 25.08.2026 14:00</i>"
        )
        return

    now = datetime.now(_TZ)
    if dt <= now:
        await msg.answer("❌ Muddat kelajakda bo'lishi kerak.")
        return

    data = await state.get_data()
    await state.clear()

    profile = await _get_profile(msg.from_user.id)
    if profile is None:
        return

    async with session_factory() as session:
        pd = PersonalDeadline(
            student_profile_id=profile.id,
            title=data["title"],
            deadline_at=dt,
        )
        session.add(pd)
        await session.commit()

    await msg.answer(
        f"✅ Eslatma saqlandi!\n\n"
        f"📝 <b>{data['title']}</b>\n"
        f"🗓 {_fmt_dt(dt)}\n"
        f"{_time_left(dt)}\n\n"
        f"24 soat va 2 soat qolganida xabar yuboraman."
    )
