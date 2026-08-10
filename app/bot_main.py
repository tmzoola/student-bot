"""Bot polling + fon xizmatlari uchun alohida process.

WebApp uvicorn worker'larida polling ishlamaydi — bu yerda bitta markaziy
process ishga tushiradi. Shu bilan `--workers N` bilan ishlaganda
`TelegramConflictError` yuz bermaydi.

Docker: `docker-compose.yml` da alohida `bot` xizmati bu modulni ishga tushiradi.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from bot.setup import ALLOWED_UPDATES, bot, dp
from core.config import settings
from logging_config import setup_logging

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Tashkent")
_REENGAGEMENT_HOUR = 10


async def _reengagement_loop() -> None:
    from services.notifications import send_reengagement_notifications

    while True:
        now = datetime.now(_TZ)
        next_run = now.replace(hour=_REENGAGEMENT_HOUR, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)
        wait = (next_run - now).total_seconds()
        logger.info("Reengagement: next run in %.0f s (%s)", wait, next_run.isoformat())
        await asyncio.sleep(wait)
        try:
            stats = await send_reengagement_notifications(settings.WEBAPP_URL)
            logger.info("Reengagement done: %s", stats)
        except Exception:
            logger.exception("Reengagement notification error")


async def main() -> None:
    setup_logging()

    from aiogram.types import BotCommand, BotCommandScopeDefault

    try:
        await bot.set_my_commands(
            [BotCommand(command="start", description="Botni ishga tushirish")],
            scope=BotCommandScopeDefault(),
        )
    except Exception:
        logger.exception("set_my_commands failed")

    logger.info("▶ Bot polling + workers starting")

    from services.deadline_notifier import run_deadline_checker

    tasks = [
        asyncio.create_task(
            dp.start_polling(bot, skip_updates=True, allowed_updates=ALLOWED_UPDATES),
            name="polling",
        ),
        asyncio.create_task(_reengagement_loop(), name="reengagement"),
        asyncio.create_task(run_deadline_checker(bot), name="deadline_checker"),
    ]

    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.cancel()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
