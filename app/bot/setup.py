import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.admin_approval import router as admin_approval_router
from bot.handlers.calendar import router as calendar_router
from bot.handlers.materials import router as materials_router
from bot.handlers.menu import router as menu_router
from bot.handlers.registration import router as registration_router
from bot.middlewares import BlacklistMiddleware, RegistrationGateMiddleware
from core.config import settings

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# FSM holati Redis'da saqlanadi — shunda bot va app jarayonlari bir xil holatni
# ko'radi. Redis mavjud bo'lmasa xotira'ga tushamiz.
try:
    from aiogram.fsm.storage.redis import RedisStorage

    _storage = RedisStorage.from_url(settings.REDIS_URL)
    logger.info("✅ FSM storage: Redis (%s)", settings.REDIS_URL)
except Exception:  # noqa: BLE001
    logger.exception("Redis FSM storage o'rnatilmadi — MemoryStorage'ga qaytildi")
    _storage = MemoryStorage()

dp = Dispatcher(storage=_storage)
_blacklist = BlacklistMiddleware()
_reg_gate = RegistrationGateMiddleware()
dp.message.outer_middleware(_blacklist)
dp.callback_query.outer_middleware(_blacklist)
dp.message.outer_middleware(_reg_gate)
dp.callback_query.outer_middleware(_reg_gate)
dp.include_router(admin_approval_router)
dp.include_router(calendar_router)
dp.include_router(menu_router)
dp.include_router(materials_router)
dp.include_router(registration_router)

# Refaktor bosqichi: referral bilan bog'liq router'lar (chat_member, join
# request, inline) T-105 doirasida olib tashlandi. Student-bot uchun kerakli
# update turlari keyingi bosqichlarda qayta hisoblanadi.
ALLOWED_UPDATES: list[str] = [
    "message",
    "edited_message",
    "callback_query",
]
