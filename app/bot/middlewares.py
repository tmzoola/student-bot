import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update
from sqlalchemy import select

from db.session import session_factory
from models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)

BAN_MESSAGE = "⛔ Siz bloklangansiz. Bot administratori bilan bog'laning."


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
