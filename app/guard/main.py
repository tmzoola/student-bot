"""Guard boti (@tozakanal_bot) — alohida jarayon/konteyner.

Guruhga yangi qo'shilganlarni 18+ profilga tekshiradi, jurnalga yozadi va
adminni ogohlantiradi. edu-bot bilan bir xil Postgres'dan foydalanadi;
natijalar edu-bot admin panelida ko'rinadi.

Ishga tushirish (app/ ichidan):  python -m guard.main
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import text

from core.config import settings
from db.session import engine
from guard.handlers import router
from models.base import Base
from models.guard import FlaggedUser, JoinEvent

logger = logging.getLogger(__name__)


async def _ensure_tables() -> None:
    """Guard jadvallarini yaratadi (faqat shu ikkitasi — boshqasiga tegmaydi)."""
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[JoinEvent.__table__, FlaggedUser.__table__],
        )
        # Eski o'rnatishlar uchun keyin qo'shilgan ustunlar (idempotent).
        # `create_all` mavjud jadvalga yangi ustun qo'shmaydi — shuning uchun
        # NSFW/flag ustunlarini qo'lda ADD COLUMN IF NOT EXISTS qilamiz, aks
        # holda admin panel so'rovi (masalan `nsfw_score`) 500 beradi.
        _patches = [
            "ALTER TABLE guard_join_events "
            "ADD COLUMN IF NOT EXISTS has_photo BOOLEAN NOT NULL DEFAULT false",
            "ALTER TABLE guard_join_events "
            "ADD COLUMN IF NOT EXISTS nsfw_score DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE guard_join_events "
            "ADD COLUMN IF NOT EXISTS flagged BOOLEAN NOT NULL DEFAULT false",
            "ALTER TABLE guard_flagged_users "
            "ADD COLUMN IF NOT EXISTS nsfw_score DOUBLE PRECISION NOT NULL DEFAULT 0",
            "ALTER TABLE guard_flagged_users "
            "ADD COLUMN IF NOT EXISTS reasons TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE guard_flagged_users "
            "ADD COLUMN IF NOT EXISTS photo_path VARCHAR(512)",
            "ALTER TABLE guard_flagged_users "
            "ADD COLUMN IF NOT EXISTS action VARCHAR(16) NOT NULL DEFAULT 'pending'",
            "ALTER TABLE guard_flagged_users "
            "ADD COLUMN IF NOT EXISTS decided_by VARCHAR(256)",
            "ALTER TABLE guard_flagged_users "
            "ADD COLUMN IF NOT EXISTS decided_at TIMESTAMP WITH TIME ZONE",
        ]
        for stmt in _patches:
            await conn.execute(text(stmt))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    if not settings.GUARD_BOT_TOKEN:
        raise SystemExit("GUARD_BOT_TOKEN o'rnatilmagan (.env)")

    await _ensure_tables()

    bot = Bot(settings.GUARD_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("✅ Guard bot polling boshlandi")
    await dp.start_polling(
        bot, allowed_updates=["chat_member", "callback_query", "message"]
    )


if __name__ == "__main__":
    asyncio.run(main())
