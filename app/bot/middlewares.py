import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from sqlalchemy import select

from core.config import settings
from db.session import session_factory
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)

BAN_MESSAGE = "⛔ Siz bloklangansiz. Bot administratori bilan bog'laning."
UNREGISTERED_MESSAGE = "Iltimos, ro'yxatdan o'ting: /start"
PENDING_MESSAGE = "Arizangiz admin tomonidan ko'rib chiqilmoqda. Iltimos, kuting."


async def _is_banned(telegram_id: int) -> bool:
    async with session_factory() as session:
        banned = await session.scalar(
            select(TelegramUser.is_banned).where(
                TelegramUser.telegram_id == telegram_id
            )
        )
        return bool(banned)


class BlacklistMiddleware(BaseMiddleware):
    """Reject every interaction from an admin-blacklisted (is_banned) user."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and await _is_banned(user.id):
            # Let the user know once, then swallow the update.
            try:
                if isinstance(event, Update) and event.message:
                    await event.message.answer(BAN_MESSAGE)
                elif isinstance(event, Message):
                    await event.answer(BAN_MESSAGE)
                elif isinstance(event, CallbackQuery):
                    await event.answer(BAN_MESSAGE, show_alert=True)
            except Exception:  # noqa: BLE001
                logger.exception("failed to notify banned user %s", user.id)
            return None
        return await handler(event, data)


def _extract_message(event: TelegramObject) -> Message | None:
    if isinstance(event, Message):
        return event
    if isinstance(event, Update):
        return event.message
    return None


def _extract_callback(event: TelegramObject) -> CallbackQuery | None:
    if isinstance(event, CallbackQuery):
        return event
    if isinstance(event, Update):
        return event.callback_query
    return None


def _is_start_command(event: TelegramObject) -> bool:
    msg = _extract_message(event)
    if msg is None or not msg.text:
        return False
    return msg.text.strip().split()[0].lower() in {"/start", "/start@" + settings.BOT_USERNAME.lower()}


async def _load_profile(telegram_id: int) -> StudentProfile | None:
    async with session_factory() as session:
        return await session.scalar(
            select(StudentProfile)
            .join(TelegramUser, TelegramUser.id == StudentProfile.telegram_user_id)
            .where(TelegramUser.telegram_id == telegram_id)
        )


class RegistrationGateMiddleware(BaseMiddleware):
    """Ro'yxatdan o'tmagan yoki tasdiqlanmagan foydalanuvchilarni cheklaydi.

    - Profil yo'q: FSM ichidagi update'lar va `/start` o'tadi, qolganlariga
      "Ro'yxatdan o'ting" xabari.
    - `is_approved=False`: faqat `/start` o'tadi (statusni ko'rsatish uchun),
      qolganlariga "Kutilmoqda" xabari.
    - Admin xabarlari (`ADMIN_CHAT_ID` chat'i) hech qachon cheklanmaydi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        # Admin chat'idagi callback'lar (approve/reject) hech qachon
        # cheklanmaydi — admin foydalanuvchi profili bo'lishi shart emas.
        chat = data.get("event_chat")
        if settings.ADMIN_CHAT_ID and chat is not None and chat.id == settings.ADMIN_CHAT_ID:
            return await handler(event, data)

        state: FSMContext | None = data.get("state")
        current_state = await state.get_state() if state else None

        profile = await _load_profile(user.id)

        if profile is None:
            # Registration FSM ichida bo'lsa yoki /start bo'lsa — o'tkazamiz.
            if current_state is not None or _is_start_command(event):
                return await handler(event, data)
            msg = _extract_message(event)
            cb = _extract_callback(event)
            if msg is not None:
                try:
                    await msg.answer(UNREGISTERED_MESSAGE)
                except Exception:  # noqa: BLE001
                    logger.exception("unregistered notify failed")
            elif cb is not None:
                try:
                    await cb.answer(UNREGISTERED_MESSAGE, show_alert=True)
                except Exception:  # noqa: BLE001
                    logger.exception("unregistered cb notify failed")
            return None

        if not profile.is_approved:
            if _is_start_command(event):
                return await handler(event, data)
            msg = _extract_message(event)
            cb = _extract_callback(event)
            if msg is not None:
                try:
                    await msg.answer(PENDING_MESSAGE)
                except Exception:  # noqa: BLE001
                    logger.exception("pending notify failed")
            elif cb is not None:
                try:
                    await cb.answer(PENDING_MESSAGE, show_alert=True)
                except Exception:  # noqa: BLE001
                    logger.exception("pending cb notify failed")
            return None

        return await handler(event, data)
