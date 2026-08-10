"""Deadline eslatmalarini yuborish xizmati.

Har 5 daqiqada ishga tushadi. Ikkita oyna:
  - 24h oynasi: deadline_at ∈ [now+23h50m, now+24h10m]
  - 2h oynasi:  deadline_at ∈ [now+1h50m, now+2h10m]

Admin deadlinelari uchun DeadlineSent jadvali orqali dublikat oldini oladi.
Shaxsiy deadlinelari uchun reminded_24h / reminded_2h maydonlari ishlatiladi.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from db.session import session_factory
from models.deadline import Deadline, DeadlineSent, PersonalDeadline
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)
_TZ = ZoneInfo("Asia/Tashkent")

_WINDOW = timedelta(minutes=10)


async def _send_safe(bot, telegram_id: int, text: str) -> bool:
    try:
        await bot.send_message(telegram_id, text)
        return True
    except TelegramForbiddenError:
        return False
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        try:
            await bot.send_message(telegram_id, text)
            return True
        except Exception:
            return False
    except Exception:
        logger.exception("deadline send error to %s", telegram_id)
        return False


async def _notify_admin_deadlines(bot, now: datetime) -> None:
    windows = {
        "24h": (now + timedelta(hours=24) - _WINDOW, now + timedelta(hours=24) + _WINDOW),
        "2h": (now + timedelta(hours=2) - _WINDOW, now + timedelta(hours=2) + _WINDOW),
    }

    async with session_factory() as session:
        for remind_type, (lo, hi) in windows.items():
            deadlines = (await session.scalars(
                select(Deadline)
                .where(
                    Deadline.is_active.is_(True),
                    Deadline.deadline_at >= lo,
                    Deadline.deadline_at <= hi,
                )
            )).all()

            if not deadlines:
                continue

            for deadline in deadlines:
                profiles_q = (
                    select(StudentProfile)
                    .options(selectinload(StudentProfile.telegram_user))
                    .join(TelegramUser, TelegramUser.id == StudentProfile.telegram_user_id)
                    .where(
                        StudentProfile.is_approved.is_(True),
                        TelegramUser.is_blocked.is_(False),
                        TelegramUser.is_banned.is_(False),
                    )
                )
                if deadline.faculty_id is not None:
                    profiles_q = profiles_q.where(StudentProfile.faculty_id == deadline.faculty_id)

                profiles = (await session.scalars(profiles_q)).all()

                already_sent_q = select(DeadlineSent.student_profile_id).where(
                    DeadlineSent.deadline_id == deadline.id,
                    DeadlineSent.remind_type == remind_type,
                )
                already_sent = set((await session.scalars(already_sent_q)).all())

                label = "24 soat" if remind_type == "24h" else "2 soat"
                dl_time = deadline.deadline_at.astimezone(_TZ).strftime("%d.%m.%Y %H:%M")
                text = (
                    f"⏰ <b>Deadline eslatmasi</b>\n\n"
                    f"📋 {deadline.title}\n"
                    f"🕒 Muddat: <b>{dl_time}</b>\n"
                    f"⚠️ Qoldi: <b>{label}</b>"
                )
                if deadline.description:
                    text += f"\n\n{deadline.description}"

                sent_count = 0
                for profile in profiles:
                    if profile.id in already_sent:
                        continue
                    ok = await _send_safe(bot, profile.telegram_user.telegram_id, text)
                    if ok:
                        session.add(DeadlineSent(
                            deadline_id=deadline.id,
                            student_profile_id=profile.id,
                            remind_type=remind_type,
                        ))
                        sent_count += 1
                    await asyncio.sleep(0.05)

                await session.commit()
                logger.info(
                    "deadline %d '%s' [%s]: %d ta xabar yuborildi",
                    deadline.id, deadline.title, remind_type, sent_count,
                )


async def _notify_personal_deadlines(bot, now: datetime) -> None:
    windows_24h = (now + timedelta(hours=24) - _WINDOW, now + timedelta(hours=24) + _WINDOW)
    windows_2h = (now + timedelta(hours=2) - _WINDOW, now + timedelta(hours=2) + _WINDOW)

    async with session_factory() as session:
        # 24h window
        pd_24 = (await session.scalars(
            select(PersonalDeadline)
            .options(selectinload(PersonalDeadline.student_profile).selectinload(StudentProfile.telegram_user))
            .where(
                PersonalDeadline.reminded_24h.is_(False),
                PersonalDeadline.deadline_at >= windows_24h[0],
                PersonalDeadline.deadline_at <= windows_24h[1],
            )
        )).all()

        for pd in pd_24:
            dl_time = pd.deadline_at.astimezone(_TZ).strftime("%d.%m.%Y %H:%M")
            text = (
                f"⏰ <b>Shaxsiy eslatma</b>\n\n"
                f"📝 {pd.title}\n"
                f"🕒 Muddat: <b>{dl_time}</b>\n"
                f"⚠️ Qoldi: <b>24 soat</b>"
            )
            tg = pd.student_profile.telegram_user
            await _send_safe(bot, tg.telegram_id, text)
            pd.reminded_24h = True
            await asyncio.sleep(0.05)

        # 2h window
        pd_2 = (await session.scalars(
            select(PersonalDeadline)
            .options(selectinload(PersonalDeadline.student_profile).selectinload(StudentProfile.telegram_user))
            .where(
                PersonalDeadline.reminded_2h.is_(False),
                PersonalDeadline.deadline_at >= windows_2h[0],
                PersonalDeadline.deadline_at <= windows_2h[1],
            )
        )).all()

        for pd in pd_2:
            dl_time = pd.deadline_at.astimezone(_TZ).strftime("%d.%m.%Y %H:%M")
            text = (
                f"⏰ <b>Shaxsiy eslatma</b>\n\n"
                f"📝 {pd.title}\n"
                f"🕒 Muddat: <b>{dl_time}</b>\n"
                f"⚠️ Qoldi: <b>2 soat</b>"
            )
            tg = pd.student_profile.telegram_user
            await _send_safe(bot, tg.telegram_id, text)
            pd.reminded_2h = True
            await asyncio.sleep(0.05)

        await session.commit()


async def run_deadline_checker(bot) -> None:
    """5 daqiqada bir marta deadline oynalarini tekshiradi."""
    while True:
        await asyncio.sleep(5 * 60)
        now = datetime.now(_TZ)
        try:
            await _notify_admin_deadlines(bot, now)
            await _notify_personal_deadlines(bot, now)
        except Exception:
            logger.exception("deadline_checker xatosi")
