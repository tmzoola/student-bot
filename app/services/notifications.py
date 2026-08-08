import asyncio
import logging
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select

from db.session import session_factory
from models.telegram_user import TelegramUser

_TZ = ZoneInfo("Asia/Tashkent")

_REENGAGEMENT_TEMPLATES = [
    (
        "Assalomu alaykum, {name}! 🌸\n\n"
        "Bir muddat ko'rinmay qoldingiz — sog'indik.\n"
        "Siz ketgandan beri yangi testlar qo'shildi.\n\n"
        "2 daqiqa, bitta test bilan qaytamizmi? 📚"
    ),
    (
        "Salom, {name}! 👋\n\n"
        "Attestatsiyanizga tayyorgarlik davom etayaptimi?\n"
        "Yangi mavzular va testlar qo'shildi — bir ko'z tashlang! 🎯"
    ),
    (
        "{name}, sog'indik! 🧡\n\n"
        "Bir necha kun ko'rinmadingiz.\n"
        "Bilimlaringizni sinab ko'rmaysizmi?\n\n"
        "Atigi 2 daqiqa — katta natija! 🚀"
    ),
    (
        "Assalomu alaykum, {name}! ✨\n\n"
        "O'qishdan ozgina dam oldingizmi? Davom etish vaqti!\n"
        "Yangi testlar sizni kutmoqda 📖"
    ),
    (
        "{name}, xayrli kun! ☀️\n\n"
        "Attestatsiyagacha vaqt o'tib ketmoqda.\n"
        "Bugun bir test yechsangiz — ertaga osonroq bo'ladi! 💪"
    ),
]

logger = logging.getLogger(__name__)


async def _target_user_ids() -> list[int]:
    async with session_factory() as session:
        rows = await session.execute(
            select(TelegramUser.telegram_id).where(
                TelegramUser.is_blocked == False,  # noqa: E712
                TelegramUser.is_banned == False,  # noqa: E712
            )
        )
        return [r[0] for r in rows.all()]


async def count_broadcast_targets() -> int:
    """Xabar yuboriladigan (bloklanmagan, banlanmagan) foydalanuvchilar soni."""
    from sqlalchemy import func

    async with session_factory() as session:
        result = await session.execute(
            select(func.count())
            .select_from(TelegramUser)
            .where(
                TelegramUser.is_blocked == False,  # noqa: E712
                TelegramUser.is_banned == False,  # noqa: E712
            )
        )
        return int(result.scalar_one())


# Fon rejimidagi task'larni GC yeb ketmasligi uchun kuchli havola saqlaymiz.
_bg_tasks: set[asyncio.Task] = set()


def fire_and_forget(coro) -> asyncio.Task:
    """Coroutine'ni request umridan mustaqil fon task sifatida ishga tushiradi.

    So'rov (yoki reverse-proxy) uzilsa ham task bekor bo'lmaydi — uzoq davom
    etadigan broadcast to'liq yakuniga yetadi.
    """
    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    return task


async def _mark_blocked(telegram_id: int) -> None:
    async with session_factory() as session:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user and not user.is_blocked:
            user.is_blocked = True
            await session.commit()


async def broadcast(
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> dict[str, int]:
    """Send `text` to every non-blocked user. Returns delivery stats."""
    from bot.setup import bot  # local import — avoid startup cycles

    user_ids = await _target_user_ids()
    sent = failed = blocked = 0

    for tg_id in user_ids:
        try:
            await bot.send_message(tg_id, text, reply_markup=reply_markup)
            sent += 1
        except TelegramForbiddenError:
            blocked += 1
            try:
                await _mark_blocked(tg_id)
            except Exception:  # noqa: BLE001
                logger.exception("broadcast: _mark_blocked failed for %s", tg_id)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(tg_id, text, reply_markup=reply_markup)
                sent += 1
            except Exception:  # noqa: BLE001
                failed += 1
        except Exception:  # noqa: BLE001
            failed += 1
            logger.exception("broadcast failed for %s", tg_id)

        # Telegram allows ~30 msgs/sec; keep well under.
        await asyncio.sleep(0.05)

    logger.info("broadcast: sent=%s blocked=%s failed=%s", sent, blocked, failed)
    return {"total": len(user_ids), "sent": sent, "blocked": blocked, "failed": failed}


async def notify_new_quiz(quiz_id: int, quiz_title: str, webapp_base: str) -> dict[str, int]:
    text = (
        "🆕 <b>Yangi test qo'shildi!</b>\n\n"
        f"📚 <b>{quiz_title}</b>\n\n"
        "Testni yechish uchun quyidagi tugmani bosing 👇"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🚀 Testni ochish",
                web_app=WebAppInfo(url=f"{webapp_base}/webapp/quiz/{quiz_id}"),
            )
        ]]
    )
    return await broadcast(text, reply_markup=kb)


async def _inactive_users(days: int = 3) -> list[TelegramUser]:
    """Return registered, non-blocked users inactive for `days` days."""
    cutoff = datetime.now(_TZ) - timedelta(days=days)
    async with session_factory() as session:
        rows = await session.execute(
            select(TelegramUser).where(
                TelegramUser.is_blocked == False,  # noqa: E712
                TelegramUser.is_banned == False,  # noqa: E712
                TelegramUser.phone.is_not(None),
                TelegramUser.last_active_at.is_not(None),
                TelegramUser.last_active_at < cutoff,
            )
        )
        return list(rows.scalars().all())


async def send_reengagement_notifications(webapp_base: str) -> dict[str, int]:
    """Send personalised re-engagement messages to users inactive 3+ days."""
    from bot.setup import bot  # local import — avoid startup cycles

    users = await _inactive_users(days=3)
    sent = failed = blocked = 0

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📚 Testlarni ochish",
                web_app=WebAppInfo(url=f"{webapp_base}/webapp/modules"),
            )
        ]]
    )

    for user in users:
        name = user.last_name or user.first_name or user.username or "Foydalanuvchi"
        text = random.choice(_REENGAGEMENT_TEMPLATES).format(name=name)
        try:
            await bot.send_message(user.telegram_id, text, reply_markup=kb)
            sent += 1
        except TelegramForbiddenError:
            blocked += 1
            await _mark_blocked(user.telegram_id)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(user.telegram_id, text, reply_markup=kb)
                sent += 1
            except Exception:  # noqa: BLE001
                failed += 1
        except Exception:  # noqa: BLE001
            failed += 1
            logger.exception("reengagement failed for %s", user.telegram_id)
        await asyncio.sleep(0.05)

    logger.info(
        "reengagement: users=%s sent=%s blocked=%s failed=%s",
        len(users), sent, blocked, failed,
    )
    return {"total": len(users), "sent": sent, "blocked": blocked, "failed": failed}
