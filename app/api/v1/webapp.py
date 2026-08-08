"""WebApp uchun HTML sahifalar va minimal JSON API.

Refaktor bosqichi: T-102 doirasida kitob/do'kon/kontent legacy endpoint'lari
olib tashlandi. Faqat quiz/topic/mavzu sahifalari qoldi. Student-bot uchun
to'liq API keyingi bosqichlarda (student auth, WebApp UI) qayta yoziladi.
"""
import hashlib
import hmac
import logging

from core.config import settings
from db.session import get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models.telegram_user import TelegramUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

pages = APIRouter(prefix="/webapp", tags=["webapp-pages"])
api = APIRouter(prefix="/api/v1/webapp", tags=["webapp-api"])

templates = Jinja2Templates(directory="templates")


# ═══ Bot token (bot -> WebApp uzatiladigan qisqa muddatli imzo) ══════

def make_bot_token(telegram_id: int, ttl_seconds: int = 3600) -> str:
    import time
    exp = int(time.time()) + ttl_seconds
    msg = f"{telegram_id}.{exp}"
    sig = hmac.new(settings.SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def _verify_bot_token(token: str) -> int | None:
    import time
    try:
        tg_id_s, exp_s, sig = token.split(".")
        tg_id = int(tg_id_s)
        exp = int(exp_s)
        if time.time() > exp:
            return None
        msg = f"{tg_id_s}.{exp_s}"
        expected = hmac.new(settings.SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return None
        return tg_id
    except Exception:  # noqa: BLE001
        return None


# ═══ Redis kliyenti (health uchun kerak) ═════════════════════════════

try:
    import redis.asyncio as _aioredis  # type: ignore
    _redis = _aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=2,
        socket_connect_timeout=2,
    )
except Exception:  # noqa: BLE001
    logger.exception("Redis client init failed")
    _redis = None


# ═══ HTML sahifalar (quiz/topic minimal) ═════════════════════════════

@pages.get("/", response_class=HTMLResponse)
async def landing(request: Request, db: AsyncSession = Depends(get_db), t: str | None = None):
    if t:
        tg_id = _verify_bot_token(t)
        if tg_id:
            result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == tg_id))
            user = result.scalar_one_or_none()
            if user and not user.is_banned:
                request.session["mk_tg_id"] = user.telegram_id
    return templates.TemplateResponse("index.html", {"request": request, "content": None})


@pages.get("/topics/{topic_id}", response_class=HTMLResponse)
async def topic_quizzes_page(request: Request, topic_id: int):
    return templates.TemplateResponse("quizzes.html", {"request": request, "topic_id": topic_id})


@pages.get("/quiz/{quiz_id}", response_class=HTMLResponse)
async def quiz_page(request: Request, quiz_id: int):
    return templates.TemplateResponse("quiz.html", {"request": request, "quiz_id": quiz_id})


@pages.get("/results/{attempt_id}", response_class=HTMLResponse)
async def results_page(request: Request, attempt_id: int):
    return templates.TemplateResponse("results.html", {"request": request, "attempt_id": attempt_id})


@pages.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse("leaderboard.html", {"request": request})


@pages.get("/me", response_class=HTMLResponse)
async def me_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


@pages.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})


@pages.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@pages.get("/daily", response_class=HTMLResponse)
async def daily_page(request: Request):
    return templates.TemplateResponse("daily.html", {"request": request})


# ═══ Minimal JSON API stub ═══════════════════════════════════════════
# To'liq student-bot API keyingi bosqichlarda yoziladi (T-1XX).

@api.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    tg_id = request.session.get("mk_tg_id")
    if not tg_id:
        raise HTTPException(status_code=401, detail="not authenticated")
    result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
