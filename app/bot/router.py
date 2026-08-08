"""Umumiy bot util'lari.

`/start` va boshqa handler'lar `bot/handlers/` ichidagi router'larda joylashgan.
Bu modul faqat umumiy yordamchi funksiyalar (`get_or_create_user`) uchun ishlatiladi.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from db.session import session_factory
from models.telegram_user import TelegramUser

_TZ = ZoneInfo("Asia/Tashkent")
logger = logging.getLogger(__name__)


async def get_or_create_user(tg_user) -> TelegramUser:
    async with session_factory() as session:
        stmt = select(TelegramUser).where(TelegramUser.telegram_id == tg_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        now = datetime.now(_TZ)
        if not user:
            user = TelegramUser(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language_code=tg_user.language_code,
                last_active_at=now,
            )
            session.add(user)
        else:
            if not user.last_active_at or (now - user.last_active_at).total_seconds() > 3600:
                user.last_active_at = now
        await session.commit()
        await session.refresh(user)
        return user
