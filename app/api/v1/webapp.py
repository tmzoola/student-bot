import hashlib
import hmac
import json
import logging
import random
import re
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl

from pathlib import Path as FsPath

from core.config import BOOK_CATEGORIES, MEDIA_ROOT, settings
from db.session import get_db
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from models.attempt import QuizAttempt
from models.base import TASHKENT_TZ
from models.book import Book
from models.contest import Contest, ContestAttempt, ContestQuestion
from models.landing import LandingContent
from models.module import Module
from models.question import Question
from models.quiz import Quiz
from models.shop import BookOrder, ShopBook, ShopSettings
from models.telegram_user import TelegramUser
from models.topic import Topic
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

# HTML pages
pages = APIRouter(prefix="/webapp", tags=["webapp-pages"])
# JSON API
api = APIRouter(prefix="/api/v1/webapp", tags=["webapp-api"])

templates = Jinja2Templates(directory="templates")


# ═══ HTML pages ══════════════════════════════════════════════════════

def make_bot_token(telegram_id: int, ttl_seconds: int = 3600) -> str:
    """Bot tomondan yaratiladigan qisqa muddatli imzolangan token.
    Format: <tg_id>.<exp>.<hex_hmac>. WebApp URL'iga `?t=` sifatida qo'shiladi.
    """
    import time
    exp = int(time.time()) + ttl_seconds
    msg = f"{telegram_id}.{exp}"
    sig = hmac.new(settings.SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return f"{msg}.{sig}"


def _verify_bot_token(token: str) -> int | None:
    """Tokenni tekshiradi va telegram_id qaytaradi, aks holda None."""
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


@pages.get("/", response_class=HTMLResponse)
async def landing(request: Request, db: AsyncSession = Depends(get_db), t: str | None = None):
    # Bot bergan tokenni tekshirib, session cookie'ni o'rnatamiz. Bu iOS
    # Telegram Mini App'da initData ba'zan bo'sh kelishi muammosini yopadi.
    if t:
        tg_id = _verify_bot_token(t)
        if tg_id:
            result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == tg_id))
            user = result.scalar_one_or_none()
            if user and not user.is_banned:
                request.session["mk_tg_id"] = user.telegram_id
    row = (await db.execute(
        select(LandingContent).where(LandingContent.deletedAt.is_(None)).limit(1)
    )).scalar_one_or_none()
    return templates.TemplateResponse("index.html", {"request": request, "content": row})


@pages.get("/modules", response_class=HTMLResponse)
async def modules_page(request: Request):
    return templates.TemplateResponse("modules.html", {"request": request})


@pages.get("/modules/{module_id}", response_class=HTMLResponse)
async def module_topics_page(request: Request, module_id: int):
    # Topics view is hidden from users for now; jumps straight to quizzes.
    # The template is kept for the future when there will be many quizzes per module.
    # return templates.TemplateResponse("topics.html", {"request": request, "module_id": module_id})
    return templates.TemplateResponse(
        "module_quizzes.html", {"request": request, "module_id": module_id}
    )


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
async def settings_page(request: Request, db: AsyncSession = Depends(get_db), t: str | None = None):
    if t:
        tg_id = _verify_bot_token(t)
        if tg_id:
            result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == tg_id))
            user = result.scalar_one_or_none()
            if user and not user.is_banned:
                request.session["mk_tg_id"] = user.telegram_id
    return templates.TemplateResponse("settings.html", {"request": request})


@pages.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@pages.get("/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request):
    return templates.TemplateResponse("subscribe.html", {"request": request})


@pages.get("/daily", response_class=HTMLResponse)
async def daily_page(request: Request):
    return templates.TemplateResponse("daily.html", {"request": request})


@pages.get("/contests", response_class=HTMLResponse)
async def contests_page(request: Request):
    return templates.TemplateResponse("contests.html", {"request": request})


@pages.get("/contests/{contest_id}", response_class=HTMLResponse)
async def contest_detail_page(request: Request, contest_id: int):
    return templates.TemplateResponse(
        "contest_detail.html", {"request": request, "contest_id": contest_id}
    )


@pages.get("/contests/{contest_id}/play", response_class=HTMLResponse)
async def contest_play_page(request: Request, contest_id: int):
    return templates.TemplateResponse(
        "contest_play.html", {"request": request, "contest_id": contest_id}
    )


@pages.get("/contests/{contest_id}/winners", response_class=HTMLResponse)
async def contest_winners_web_page(request: Request, contest_id: int):
    return templates.TemplateResponse(
        "contest_winners.html", {"request": request, "contest_id": contest_id}
    )


@pages.get("/contests/{contest_id}/review", response_class=HTMLResponse)
async def contest_review_page(request: Request, contest_id: int):
    return templates.TemplateResponse(
        "contest_review.html", {"request": request, "contest_id": contest_id}
    )


@pages.get("/books", response_class=HTMLResponse)
async def books_page(request: Request):
    return templates.TemplateResponse("books.html", {"request": request})


@pages.get("/my-orders", response_class=HTMLResponse)
async def my_orders_page(request: Request):
    return templates.TemplateResponse("my_orders.html", {"request": request})


@pages.get("/books/{book_id}/file")
async def book_file(book_id: int, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if not book or not book.is_active:
        raise HTTPException(404, "Kitob topilmadi")
    path = MEDIA_ROOT / book.file_path
    if not path.is_file():
        raise HTTPException(404, "Fayl topilmadi")
    book.downloads += 1
    await db.commit()
    return FileResponse(path, filename=book.file_name)


# ═══ Telegram initData validation ════════════════════════════════════

def _verify_telegram_init_data(init_data: str) -> dict[str, Any] | None:
    """Return decoded user dict if HMAC matches, else None."""
    if not init_data:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        hash_from_client = parsed.pop("hash", None)
        if not hash_from_client:
            return None
        data_check_string = "\n".join(f"{k}={parsed[k]}" for k in sorted(parsed))
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, hash_from_client):
            return None
        user_json = parsed.get("user")
        if not user_json:
            return None
        return json.loads(user_json)
    except Exception:  # noqa: BLE001
        logger.exception("initData verification failed")
        return None


async def _get_or_create_tg_user(db: AsyncSession, tg_data: dict[str, Any]) -> TelegramUser:
    tg_id = int(tg_data["id"])
    result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    now = datetime.now(TASHKENT_TZ)
    if user:
        # Keep Telegram-managed fields in sync, but DO NOT overwrite the
        # user's name — they can edit it in WebApp settings, and re-syncing
        # from initData on every request would revert those edits.
        user.username = tg_data.get("username") or user.username
        user.language_code = tg_data.get("language_code") or user.language_code
        if not user.first_name:
            user.first_name = tg_data.get("first_name")
        if not user.last_name:
            user.last_name = tg_data.get("last_name")
        # Refresh at most once per hour to avoid excessive writes.
        if not user.last_active_at or (now - user.last_active_at).total_seconds() > 3600:
            user.last_active_at = now
        return user
    user = TelegramUser(
        telegram_id=tg_id,
        first_name=tg_data.get("first_name"),
        last_name=tg_data.get("last_name"),
        username=tg_data.get("username"),
        language_code=tg_data.get("language_code"),
        last_active_at=now,
    )
    db.add(user)
    await db.flush()
    return user


async def _resolve_user(
    db: AsyncSession,
    x_init_data: str | None,
    x_tg_id: int | None,  # noqa: ARG001 — qabul qilinadi, ammo ishonchsiz
    request: Request | None = None,
) -> TelegramUser | None:
    """Faqat imzolangan manbalarga ishonadi:
      1) `X-Init-Data` — Telegram tomonidan bot token bilan HMAC-imzolangan;
      2) Server session cookie (`mk_tg_id`) — biz oldingi so'rovda o'rnatgan.
    `X-Telegram-Id` header'iga ishonmaydi — u imzosiz va boshqa foydalanuvchi
    sifatida kirish uchun ishlatilishi mumkin edi.
    """
    if x_init_data:
        tg = _verify_telegram_init_data(x_init_data)
        if tg:
            user = await _get_or_create_tg_user(db, tg)
            await db.commit()
            if user.is_banned:
                raise HTTPException(403, "Siz bloklangansiz")
            if request is not None:
                request.session["mk_tg_id"] = user.telegram_id
            return user
    # Session cookie'da saqlangan telegram_id (landing sahifada auth qilingan)
    if request is not None:
        sess_tg = request.session.get("mk_tg_id")
        if sess_tg:
            result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == int(sess_tg)))
            user = result.scalar_one_or_none()
            if user:
                if user.is_banned:
                    raise HTTPException(403, "Siz bloklangansiz")
                return user
    return None


# ═══ Subscription gate helpers ═══════════════════════════════════════

# Redis'da 60 soniya keshlanadi. Multi-worker (uvicorn --workers N) va bot
# konteyner o'rtasida umumiy — har workerda alohida kesh saqlanmaydi.
_SUB_TTL_SECONDS = 60

# O'zbekiston mobil raqam: +998 XX XXX XX XX (operator kodlari: 9X, 33, 55, 77, 88)
_UZ_PHONE_RE = re.compile(
    r"^(\+?998)?\s?(9[0-9]|33|55|77|88)\s?\d{3}\s?\d{2}\s?\d{2}$"
)

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
    logger.exception("Redis client init failed — sub cache o'chirildi")
    _redis = None


def _sub_key(user_tg_id: int) -> str:
    return f"mk:sub:{user_tg_id}"


async def _sub_cache_invalidate(user_tg_id: int) -> None:
    if _redis is None:
        return
    try:
        await _redis.delete(_sub_key(user_tg_id))
    except Exception:  # noqa: BLE001
        logger.warning("Redis DEL xatosi: tg=%s", user_tg_id)


async def _subscription_state(db: AsyncSession, user_tg_id: int) -> dict[str, Any]:
    """Foydalanuvchi barcha faol tracked chatlarga a'zomi — tekshirib qaytaradi.
    Xato bo'lsa (bot yo'q, tarmoq muammosi, ...) — jimgina "ok" deb olamiz,
    aks holda butun WebApp ishlamay qoladi.
    """
    # 1) Redis'dan kesh olishga urinamiz.
    if _redis is not None:
        try:
            raw = await _redis.get(_sub_key(user_tg_id))
            if raw:
                return json.loads(raw)
        except Exception:  # noqa: BLE001
            logger.warning("Redis GET xatosi: tg=%s", user_tg_id)

    from bot.setup import bot
    from services.referral.events import chat_join_url
    from services.referral.membership import check_subscription

    try:
        ok, missing = await check_subscription(db, bot, user_tg_id=user_tg_id)
    except Exception:  # noqa: BLE001
        logger.exception("check_subscription xatosi: tg=%s", user_tg_id)
        # Xatolik — WebApp ishlashda davom etsin, keshlamaymiz.
        return {"must_subscribe": False, "missing_chats": []}

    state = {
        "must_subscribe": not ok,
        "missing_chats": [
            {
                "title": c.title,
                "type": c.type,
                "url": chat_join_url(c),
            }
            for c in missing
        ],
    }

    if _redis is not None:
        try:
            await _redis.setex(
                _sub_key(user_tg_id),
                _SUB_TTL_SECONDS,
                json.dumps(state, ensure_ascii=False),
            )
        except Exception:  # noqa: BLE001
            logger.warning("Redis SETEX xatosi: tg=%s", user_tg_id)

    return state


async def _require_subscribed(db: AsyncSession, user_tg_id: int) -> None:
    state = await _subscription_state(db, user_tg_id)
    if state["must_subscribe"]:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "must_subscribe",
                "missing_chats": state["missing_chats"],
            },
        )


# ═══ Auth endpoint ═══════════════════════════════════════════════════

@api.post("/auth")
async def auth(request: Request, payload: dict[str, Any], db: AsyncSession = Depends(get_db)):
    init_data = (payload or {}).get("init_data") or ""
    tg = _verify_telegram_init_data(init_data)

    if not tg:
        raw = (payload or {}).get("user") or {}
        try:
            uid = int(raw.get("id"))
        except (TypeError, ValueError):
            uid = 0
        if uid > 0:
            tg = raw

    user: TelegramUser | None = None
    if tg:
        user = await _get_or_create_tg_user(db, tg)
        await db.commit()
    else:
        # initData/user yo'q — session cookie orqali topamiz (landing'da o'rnatilgan)
        sess_tg = request.session.get("mk_tg_id")
        if sess_tg:
            result = await db.execute(select(TelegramUser).where(TelegramUser.telegram_id == int(sess_tg)))
            user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(401, "initData tekshiruvidan o'tmadi")

    if user.is_banned:
        raise HTTPException(403, "Siz bloklangansiz")

    # Session cookie'ni yangilaymiz — keyingi sahifalar initData'siz auth qila oladi.
    request.session["mk_tg_id"] = user.telegram_id

    sub_state = await _subscription_state(db, user.telegram_id)
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "phone": user.phone,
        "is_registered": user.is_registered,
        **sub_state,
    }


@api.get("/subscription/check")
async def subscription_check(
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")
    # Foydalanuvchi "Tekshirish" bosdi — kesh eskirgan bo'lishi mumkin
    # (endi kanalga qo'shilgan bo'lishi mumkin). Toza natija olamiz.
    await _sub_cache_invalidate(user.telegram_id)
    return await _subscription_state(db, user.telegram_id)


# ═══ Public content ══════════════════════════════════════════════════

@api.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    topics_count = await db.scalar(
        select(func.count()).select_from(Topic).where(Topic.is_active == True)  # noqa: E712
    ) or 0
    questions_count = await db.scalar(select(func.count()).select_from(Question)) or 0
    modules_count = await db.scalar(
        select(func.count()).select_from(Module).where(Module.is_active == True)  # noqa: E712
    ) or 0
    return {
        "topics_count": topics_count,
        "questions_count": questions_count,
        "modules_count": modules_count,
    }


@api.get("/modules")
async def list_modules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Module).where(Module.is_active == True).order_by(Module.order, Module.id)  # noqa: E712
    )
    modules = result.scalars().all()

    counts: dict[int, int] = {}
    quiz_counts: dict[int, int] = {}
    if modules:
        ids = [m.id for m in modules]
        rows = await db.execute(
            select(Topic.module_id, func.count(Topic.id))
            .where(Topic.module_id.in_(ids), Topic.is_active == True)  # noqa: E712
            .group_by(Topic.module_id)
        )
        counts = dict(rows.all())

        # Quizzes attached to module via topic (eski oqim)
        qrows = await db.execute(
            select(Topic.module_id, func.count(Quiz.id))
            .join(Quiz, Quiz.topic_id == Topic.id)
            .where(
                Topic.module_id.in_(ids),
                Topic.is_active == True,  # noqa: E712
                Quiz.is_active == True,  # noqa: E712
            )
            .group_by(Topic.module_id)
        )
        for module_id_, cnt in qrows.all():
            quiz_counts[module_id_] = quiz_counts.get(module_id_, 0) + cnt

        # Quizzes attached to module directly (yangi oqim, mavzusiz) —
        # topic_id NULL bo'lganlarini alohida qo'shamiz (aks holda double-count).
        drows = await db.execute(
            select(Quiz.module_id, func.count(Quiz.id))
            .where(
                Quiz.module_id.in_(ids),
                Quiz.topic_id.is_(None),
                Quiz.is_active == True,  # noqa: E712
            )
            .group_by(Quiz.module_id)
        )
        for module_id_, cnt in drows.all():
            quiz_counts[module_id_] = quiz_counts.get(module_id_, 0) + cnt

    return [
        {
            "id": m.id,
            "title": m.title,
            "description": m.description,
            "icon": m.icon,
            "color": m.color,
            "topic_count": counts.get(m.id, 0),
            "quiz_count": quiz_counts.get(m.id, 0),
        }
        for m in modules
    ]


@api.get("/modules/{module_id}/topics")
async def module_topics(module_id: int, db: AsyncSession = Depends(get_db)):
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(404, "Modul topilmadi")

    result = await db.execute(
        select(Topic)
        .where(Topic.module_id == module_id, Topic.is_active == True)  # noqa: E712
        .order_by(Topic.order, Topic.id)
    )
    topics = result.scalars().all()

    quiz_counts = {}
    if topics:
        ids = [t.id for t in topics]
        rows = await db.execute(
            select(Quiz.topic_id, func.count(Quiz.id))
            .where(Quiz.topic_id.in_(ids), Quiz.is_active == True)  # noqa: E712
            .group_by(Quiz.topic_id)
        )
        quiz_counts = dict(rows.all())

    return {
        "module": {"id": module.id, "title": module.title, "description": module.description},
        "topics": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "quiz_count": quiz_counts.get(t.id, 0),
            }
            for t in topics
        ],
    }


@api.get("/modules/{module_id}/quizzes")
async def module_quizzes(module_id: int, db: AsyncSession = Depends(get_db)):
    """Flat list of all quizzes across the module's topics (topic screen skipped)."""
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(404, "Modul topilmadi")

    # Quiz modul bilan ikki xil bog'lanishi mumkin:
    #   (a) to'g'ridan-to'g'ri Quiz.module_id (yangi oqim, mavzusiz),
    #   (b) Quiz.topic → Topic.module_id (eski oqim, mavzu bilan).
    quizzes = (
        await db.execute(
            select(Quiz)
            .outerjoin(Topic, Topic.id == Quiz.topic_id)
            .where(
                Quiz.is_active == True,  # noqa: E712
                or_(
                    Quiz.module_id == module_id,
                    and_(Topic.module_id == module_id, Topic.is_active == True),  # noqa: E712
                ),
            )
            .options(selectinload(Quiz.topic))
            .order_by(Quiz.id)
        )
    ).scalars().all()

    q_counts: dict[int, int] = {}
    if quizzes:
        ids = [q.id for q in quizzes]
        rows = await db.execute(
            select(Question.quiz_id, func.count(Question.id))
            .where(Question.quiz_id.in_(ids))
            .group_by(Question.quiz_id)
        )
        q_counts = dict(rows.all())

    return {
        "module": {"id": module.id, "title": module.title, "description": module.description},
        "quizzes": [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "time_limit_seconds": q.time_limit_seconds,
                "question_count": q_counts.get(q.id, 0),
                "topic_title": q.topic.title if q.topic else None,
            }
            for q in quizzes
        ],
    }


@api.get("/topics/{topic_id}/quizzes")
async def topic_quizzes(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = await db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(404, "Mavzu topilmadi")

    result = await db.execute(
        select(Quiz)
        .where(Quiz.topic_id == topic_id, Quiz.is_active == True)  # noqa: E712
        .order_by(Quiz.id)
    )
    quizzes = result.scalars().all()

    q_counts = {}
    if quizzes:
        ids = [q.id for q in quizzes]
        rows = await db.execute(
            select(Question.quiz_id, func.count(Question.id))
            .where(Question.quiz_id.in_(ids))
            .group_by(Question.quiz_id)
        )
        q_counts = dict(rows.all())

    return {
        "topic": {"id": topic.id, "title": topic.title},
        "quizzes": [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "time_limit_seconds": q.time_limit_seconds,
                "question_count": q_counts.get(q.id, 0),
            }
            for q in quizzes
        ],
    }


@api.get("/quiz/{quiz_id}")
async def get_quiz(quiz_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Quiz)
        .where(Quiz.id == quiz_id, Quiz.is_active == True)  # noqa: E712
        .options(selectinload(Quiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(404, "Test topilmadi")

    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "time_limit_seconds": quiz.time_limit_seconds,
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "image_url": q.image_url,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
                # correct_option intentionally omitted
            }
            for q in sorted(quiz.questions, key=lambda x: x.order)
        ],
    }


@api.post("/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: int,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")
    await _require_subscribed(db, user.telegram_id)

    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz_id).options(selectinload(Quiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(404, "Test topilmadi")

    answers: dict = payload.get("answers", {})
    time_taken = int(payload.get("time_taken_seconds") or 0)

    # Clamp to quiz time limit
    if time_taken <= 0 or time_taken > quiz.time_limit_seconds:
        time_taken = quiz.time_limit_seconds

    score = 0
    total = len(quiz.questions)
    for q in quiz.questions:
        chosen = answers.get(str(q.id))
        if chosen and chosen == q.correct_option.value:
            score += 1

    attempt = QuizAttempt(
        user_id=user.id,
        quiz_id=quiz_id,
        score=score,
        total=total,
        time_taken_seconds=time_taken,
        answers=answers,
        completed_at=datetime.now(TASHKENT_TZ),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    return {
        "attempt_id": attempt.id,
        "score": score,
        "total": total,
        "points": attempt.points,
        "time_taken_seconds": time_taken,
    }


@api.get("/results/{attempt_id}")
async def get_results(attempt_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.id == attempt_id)
        .options(selectinload(QuizAttempt.quiz).selectinload(Quiz.questions))
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(404, "Natija topilmadi")

    # ── Per-question review ─────────────────────────────────────────
    user_answers = attempt.answers or {}
    questions_review = []
    for q in sorted(attempt.quiz.questions, key=lambda x: x.order):
        chosen = user_answers.get(str(q.id))
        correct = q.correct_option.value
        questions_review.append({
            "id": q.id,
            "order": q.order,
            "text": q.text,
            "image_url": q.image_url,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "user_answer": chosen,
            "correct_answer": correct,
            "is_correct": chosen == correct,
            "answered": chosen is not None,
            "explanation": q.explanation,
        })

    # ── History: all attempts by same user on same quiz ────────────
    history_result = await db.execute(
        select(QuizAttempt)
        .where(
            QuizAttempt.user_id == attempt.user_id,
            QuizAttempt.quiz_id == attempt.quiz_id,
        )
        .order_by(QuizAttempt.createdAt.asc())
    )
    history_attempts = history_result.scalars().all()

    # Number them 1..N in chronological order, and mark the current one
    history = []
    current_index = 0
    best_points = 0
    for i, a in enumerate(history_attempts, start=1):
        if a.id == attempt.id:
            current_index = i
        best_points = max(best_points, a.points)
        history.append({
            "attempt_id": a.id,
            "attempt_number": i,
            "score": a.score,
            "total": a.total,
            "points": a.points,
            "percentage": a.percentage,
            "time_taken_seconds": a.time_taken_seconds,
            "date": _fmt_tashkent(a.createdAt),
            "is_current": a.id == attempt.id,
        })

    # Trend vs previous attempt
    trend = None
    if current_index > 1:
        prev = history[current_index - 2]
        cur = history[current_index - 1]
        trend = {
            "points_delta": cur["points"] - prev["points"],
            "time_delta": cur["time_taken_seconds"] - prev["time_taken_seconds"],
        }

    return {
        "attempt_id": attempt.id,
        "attempt_number": current_index,
        "total_attempts": len(history),
        "is_best": attempt.points == best_points,
        "score": attempt.score,
        "total": attempt.total,
        "points": attempt.points,
        "percentage": attempt.percentage,
        "time_taken_seconds": attempt.time_taken_seconds,
        "quiz_id": attempt.quiz.id,
        "quiz_title": attempt.quiz.title,
        "questions": questions_review,
        "history": history,
        "trend": trend,
    }


# ═══ Leaderboard ═════════════════════════════════════════════════════

_PERIODS = {"day": 1, "week": 7, "month": 30}


def _period_since(period: str) -> datetime | None:
    days = _PERIODS.get(period)
    if not days:
        return None
    return datetime.now(TASHKENT_TZ) - timedelta(days=days)


@api.get("/leaderboard")
async def leaderboard(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    period: str = "all",
):
    """
    Global leaderboard: sum of points per user (score * 2), tiebreaker by
    total time_taken_seconds ascending (faster = higher).
    Period filter: day / week / month / all — filters QuizAttempt.createdAt.
    """
    total_points = (func.sum(QuizAttempt.score) * 2).label("points")
    total_time = func.sum(QuizAttempt.time_taken_seconds).label("time_taken")
    attempts_n = func.count(QuizAttempt.id).label("attempts_n")

    stmt = (
        select(
            TelegramUser.id,
            TelegramUser.first_name,
            TelegramUser.last_name,
            TelegramUser.username,
            total_points,
            total_time,
            attempts_n,
        )
        .join(QuizAttempt, QuizAttempt.user_id == TelegramUser.id)
        .group_by(TelegramUser.id)
        .order_by(desc("points"), "time_taken")
        .limit(limit)
    )

    since = _period_since(period)
    if since is not None:
        stmt = stmt.where(QuizAttempt.createdAt >= since)

    rows = (await db.execute(stmt)).all()

    return [
        {
            "rank": i + 1,
            "user_id": r.id,
            "name": (r.first_name or r.username or f"#{r.id}"),
            "username": r.username,
            "points": int(r.points or 0),
            "time_taken_seconds": int(r.time_taken or 0),
            "attempts": int(r.attempts_n or 0),
        }
        for i, r in enumerate(rows)
    ]


@api.get("/me")
async def get_me(
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")
    sub_state = await _subscription_state(db, user.telegram_id)
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "phone": user.phone,
        "is_registered": user.is_registered,
        **sub_state,
    }


@api.post("/me/update")
async def update_me(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")

    full_name = (payload.get("full_name") or "").strip()
    phone = (payload.get("phone") or "").strip() or None

    if full_name:
        if not (2 <= len(full_name) <= 100):
            raise HTTPException(400, "Ism Familya 2 dan 100 gacha belgi bo'lishi kerak")
        parts = full_name.split(maxsplit=1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else None

    if phone is not None and phone != "":
        if not _UZ_PHONE_RE.match(phone):
            raise HTTPException(
                400,
                "Telefon raqam noto'g'ri. Format: +998 XX XXX XX XX "
                "(operator kodi: 90–99, 33, 55, 77, 88)",
            )
        user.phone = phone

    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_registered": user.is_registered,
    }


@api.get("/me/progress")
async def my_progress(
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")

    result = await db.execute(
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user.id)
        .options(selectinload(QuizAttempt.quiz))
        .order_by(QuizAttempt.createdAt.desc())
        .limit(20)
    )
    attempts = result.scalars().all()

    total_points = sum(a.points for a in attempts)
    total_attempts = await db.scalar(
        select(func.count()).select_from(QuizAttempt).where(QuizAttempt.user_id == user.id)
    ) or 0

    return {
        "user": {
            "id": user.id,
            "name": user.first_name or user.username or f"#{user.telegram_id}",
            "username": user.username,
        },
        "total_points": total_points,
        "total_attempts": total_attempts,
        "recent": [
            {
                "attempt_id": a.id,
                "quiz_title": a.quiz.title,
                "score": a.score,
                "total": a.total,
                "points": a.points,
                "time_taken_seconds": a.time_taken_seconds,
                "percentage": a.percentage,
                "date": _fmt_tashkent(a.createdAt),
            }
            for a in attempts
        ],
    }


# ═══ Motivational quote ═════════════════════════════════════════════

@api.get("/quote/today")
async def quote_today(
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    from models.quote import MotivationalQuote

    result = await db.execute(
        select(MotivationalQuote)
        .where(MotivationalQuote.is_active == True, MotivationalQuote.deletedAt.is_(None))  # noqa: E712
        .order_by(MotivationalQuote.id)
    )
    quotes = result.scalars().all()
    if not quotes:
        return {"text": None, "name": None}

    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    seed_parts = [date.today().isoformat()]
    if user:
        seed_parts.append(str(user.id))
    seed = hashlib.md5("|".join(seed_parts).encode()).hexdigest()
    idx = int(seed, 16) % len(quotes)
    q = quotes[idx]

    return {
        "text": q.text,
        "name": user.first_name if user else None,
    }


# ═══ Books ═══════════════════════════════════════════════════════════

@api.get("/books/categories")
async def book_categories(db: AsyncSession = Depends(get_db)):
    """Fixed category chips shown in the WebApp (in order)."""
    counts_rows = await db.execute(
        select(Book.category, func.count(Book.id))
        .where(Book.is_active == True)  # noqa: E712
        .group_by(Book.category)
    )
    counts = {c: n for c, n in counts_rows.all() if c}
    return [{"name": c, "count": counts.get(c, 0)} for c in BOOK_CATEGORIES]


@api.get("/books")
async def list_books(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Book)
            .where(Book.is_active == True)  # noqa: E712
            .options(selectinload(Book.topic))
            .order_by(Book.order, Book.createdAt.desc())
        )
    ).scalars().all()

    return [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "description": b.description,
            "category": b.category,
            "topic": b.topic.title if b.topic else None,
            "file_name": b.file_name,
            "file_size": b.file_size,
            "ext": FsPath(b.file_name).suffix.lstrip(".").upper(),
            "downloads": b.downloads,
            "url": f"/webapp/books/{b.id}/file",
        }
        for b in rows
    ]


# ═══ Daily quiz ══════════════════════════════════════════════════════
#
# A single "daily challenge": each day one topic is picked (rotating by date)
# and 10 questions are drawn from it. The set is deterministic — seeded by the
# date — so every user gets the same questions that day and reloads are stable.
# Attempts are stored as regular QuizAttempt rows against a hidden "Kunlik test"
# quiz, so they count toward points/leaderboard and let us compute streaks
# without a schema migration. Only the FIRST attempt of the day is official
# (awards points + extends the streak); later ones are practice.

DAILY_QUIZ_TITLE = "🗓 Kunlik test"
DAILY_TIME_LIMIT = 600
DAILY_QUESTION_COUNT = 10


def _today_tashkent() -> date:
    return datetime.now(TASHKENT_TZ).date()


def _fmt_tashkent(ts: datetime | None, fallback: str = "") -> str:
    if ts is None:
        return fallback
    if ts.tzinfo is None:
        # Legacy naive rows were written as UTC.
        from datetime import timezone as _tz
        ts = ts.replace(tzinfo=_tz.utc)
    return ts.astimezone(TASHKENT_TZ).strftime("%d.%m.%Y %H:%M")


def _attempt_date(a: QuizAttempt) -> date | None:
    ts = a.createdAt
    if ts is None:
        return None
    try:
        return ts.astimezone(TASHKENT_TZ).date()
    except Exception:  # noqa: BLE001 — naive datetimes
        return ts.date()


async def _daily_selection(db: AsyncSession, day: date | None = None):
    """Deterministic (topic, [Question]) for `day`. Same for every user."""
    day = day or _today_tashkent()
    topics = (
        await db.execute(
            select(Topic)
            .join(Quiz, Quiz.topic_id == Topic.id)
            .join(Question, Question.quiz_id == Quiz.id)
            .outerjoin(Module, Module.id == Topic.module_id)
            .where(
                Topic.is_active == True,  # noqa: E712
                Quiz.is_active == True,  # noqa: E712
                # Modul biriktirilgan bo'lsa faqat faol modul topiklari.
                or_(Topic.module_id.is_(None), Module.is_active == True),  # noqa: E712
            )
            .group_by(Topic.id)
            .order_by(Topic.order, Topic.id)
        )
    ).scalars().unique().all()
    if not topics:
        return None, []

    ordinal = day.toordinal()
    topic = topics[ordinal % len(topics)]

    pool = (
        await db.execute(
            select(Question)
            .join(Quiz, Quiz.id == Question.quiz_id)
            .outerjoin(Module, Module.id == Quiz.module_id)
            .where(
                Quiz.topic_id == topic.id,
                Quiz.is_active == True,  # noqa: E712
                or_(Quiz.module_id.is_(None), Module.is_active == True),  # noqa: E712
            )
            .order_by(Question.id)
        )
    ).scalars().all()
    if not pool:
        return topic, []

    rng = random.Random(ordinal)  # date-seeded → stable & identical for all users
    chosen = rng.sample(pool, min(DAILY_QUESTION_COUNT, len(pool)))
    return topic, chosen


async def _get_or_create_daily_quiz(db: AsyncSession) -> Quiz | None:
    """Hidden quiz row that daily attempts are recorded against."""
    quiz = (
        await db.execute(select(Quiz).where(Quiz.title == DAILY_QUIZ_TITLE))
    ).scalars().first()
    if quiz:
        return quiz
    topic = (
        await db.execute(select(Topic).order_by(Topic.id).limit(1))
    ).scalar_one_or_none()
    if not topic:
        return None
    quiz = Quiz(
        topic_id=topic.id,
        title=DAILY_QUIZ_TITLE,
        description="Har kuni bitta mavzudan 10 ta tasodifiy savol",
        time_limit_seconds=DAILY_TIME_LIMIT,
        is_active=False,  # hidden from normal topic/quiz listings
    )
    db.add(quiz)
    await db.flush()
    return quiz


async def _daily_stats(db: AsyncSession, user_id: int, daily_quiz_id: int):
    """(current_streak, today_done, today_official_attempt)."""
    attempts = (
        await db.execute(
            select(QuizAttempt)
            .where(
                QuizAttempt.user_id == user_id,
                QuizAttempt.quiz_id == daily_quiz_id,
            )
            .order_by(QuizAttempt.createdAt.asc())
        )
    ).scalars().all()

    today = _today_tashkent()
    dates: set[date] = set()
    today_official: QuizAttempt | None = None
    for a in attempts:
        d = _attempt_date(a)
        if d is None:
            continue
        dates.add(d)
        if d == today and today_official is None:
            today_official = a  # earliest attempt today = the official one

    today_done = today in dates
    anchor = today if today_done else today - timedelta(days=1)
    streak = 0
    d = anchor
    while d in dates:
        streak += 1
        d -= timedelta(days=1)
    return streak, today_done, today_official


@api.get("/daily")
async def get_daily(
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    topic, questions = await _daily_selection(db)
    if not topic or not questions:
        return {"available": False}

    resp: dict[str, Any] = {
        "available": True,
        "date": _today_tashkent().isoformat(),
        "topic_title": topic.title,
        "total": len(questions),
        "time_limit_seconds": DAILY_TIME_LIMIT,
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "image_url": q.image_url,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
            }
            for q in questions
        ],
        "today_done": False,
        "streak": 0,
        "today_result": None,
    }

    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if user:
        daily_quiz = await _get_or_create_daily_quiz(db)
        if daily_quiz:
            await db.commit()
            streak, today_done, official = await _daily_stats(db, user.id, daily_quiz.id)
            resp["streak"] = streak
            resp["today_done"] = today_done
            if official is not None:
                resp["today_result"] = {
                    "score": official.score,
                    "total": official.total,
                    "points": official.points,
                    "percentage": official.percentage,
                }
    return resp


@api.post("/daily/submit")
async def submit_daily(
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")
    await _require_subscribed(db, user.telegram_id)

    topic, questions = await _daily_selection(db)
    daily_quiz = await _get_or_create_daily_quiz(db)
    if not topic or not questions or not daily_quiz:
        raise HTTPException(400, "Kunlik test hozircha mavjud emas")

    answers: dict = payload.get("answers", {})
    time_taken = int(payload.get("time_taken_seconds") or 0)
    if time_taken <= 0 or time_taken > DAILY_TIME_LIMIT:
        time_taken = DAILY_TIME_LIMIT

    score = 0
    review = []
    for q in questions:
        correct = q.correct_option.value
        chosen = answers.get(str(q.id))
        ok = chosen == correct
        if ok:
            score += 1
        review.append({
            "id": q.id,
            "text": q.text,
            "image_url": q.image_url,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "user_answer": chosen,
            "correct_answer": correct,
            "is_correct": ok,
            "answered": chosen is not None,
            "explanation": q.explanation,
        })
    total = len(questions)

    # Only the first attempt of the day is official (awards points + streak).
    _, today_done_before, _ = await _daily_stats(db, user.id, daily_quiz.id)
    official = not today_done_before
    if official:
        db.add(QuizAttempt(
            user_id=user.id,
            quiz_id=daily_quiz.id,
            score=score,
            total=total,
            time_taken_seconds=time_taken,
            answers=answers,
            completed_at=datetime.now(TASHKENT_TZ),
        ))
        await db.commit()

    streak, today_done, _ = await _daily_stats(db, user.id, daily_quiz.id)
    return {
        "score": score,
        "total": total,
        "points": score * 2,
        "points_awarded": (score * 2) if official else 0,
        "percentage": round(score / total * 100) if total else 0,
        "official": official,
        "streak": streak,
        "today_done": today_done,
        "review": review,
    }


# ═══ Contests (yutuqli test) ════════════════════════════════════════

def _contest_state(c: Contest, now: datetime) -> str:
    if not c.is_active:
        return "inactive"
    if now < c.start_at:
        return "upcoming"
    if now > c.end_at:
        return "finished"
    return "live"


def _contest_now() -> datetime:
    return datetime.now(TASHKENT_TZ)


@api.get("/contests")
async def list_contests(
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    rows = (
        await db.execute(
            select(Contest).where(Contest.is_active == True).order_by(Contest.start_at.desc())  # noqa: E712
        )
    ).scalars().all()

    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    my_ids: set[int] = set()
    if user:
        my_rows = await db.execute(
            select(ContestAttempt.contest_id).where(ContestAttempt.user_id == user.id)
        )
        my_ids = {r[0] for r in my_rows.all()}

    counts_rows = await db.execute(
        select(ContestAttempt.contest_id, func.count(ContestAttempt.id))
        .group_by(ContestAttempt.contest_id)
    )
    counts = dict(counts_rows.all())

    now = _contest_now()
    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "prize": c.prize,
            "start_at": c.start_at.isoformat() if c.start_at else None,
            "end_at": c.end_at.isoformat() if c.end_at else None,
            "time_limit_seconds": c.time_limit_seconds,
            "question_count": c.question_count,
            "participants": counts.get(c.id, 0),
            "status": _contest_state(c, now),
            "my_participated": c.id in my_ids,
        }
        for c in rows
    ]


@api.get("/contests/{contest_id}")
async def get_contest(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    contest = await db.get(Contest, contest_id)
    if not contest or not contest.is_active:
        raise HTTPException(404, "Yutuqli test topilmadi")

    participants = await db.scalar(
        select(func.count()).select_from(ContestAttempt).where(ContestAttempt.contest_id == contest_id)
    ) or 0

    my_attempt = None
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if user:
        r = await db.execute(
            select(ContestAttempt).where(
                ContestAttempt.contest_id == contest_id,
                ContestAttempt.user_id == user.id,
            )
        )
        a = r.scalar_one_or_none()
        if a:
            my_attempt = {
                "score": a.score,
                "total": a.total,
                "percentage": a.percentage,
                "time_taken_seconds": a.time_taken_seconds,
                "completed_at": _fmt_tashkent(a.completed_at),
            }

    now = _contest_now()
    return {
        "id": contest.id,
        "title": contest.title,
        "description": contest.description,
        "prize": contest.prize,
        "start_at": contest.start_at.isoformat() if contest.start_at else None,
        "end_at": contest.end_at.isoformat() if contest.end_at else None,
        "time_limit_seconds": contest.time_limit_seconds,
        "question_count": contest.question_count,
        "participants": int(participants),
        "status": _contest_state(contest, now),
        "my_attempt": my_attempt,
    }


@api.get("/contests/{contest_id}/questions")
async def get_contest_questions(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")
    await _require_subscribed(db, user.telegram_id)

    contest = await db.get(Contest, contest_id)
    if not contest or not contest.is_active:
        raise HTTPException(404, "Yutuqli test topilmadi")

    now = _contest_now()
    state = _contest_state(contest, now)
    if state == "upcoming":
        raise HTTPException(400, "Test hali boshlanmadi")
    if state == "finished":
        raise HTTPException(400, "Test tugadi")

    # One attempt per user
    r = await db.execute(
        select(ContestAttempt).where(
            ContestAttempt.contest_id == contest_id, ContestAttempt.user_id == user.id
        )
    )
    if r.scalar_one_or_none():
        raise HTTPException(400, "Siz allaqachon ishtirok etgansiz")

    return {
        "id": contest.id,
        "title": contest.title,
        "time_limit_seconds": contest.time_limit_seconds,
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "image_url": q.image_url,
                "option_a": q.option_a,
                "option_b": q.option_b,
                "option_c": q.option_c,
                "option_d": q.option_d,
            }
            for q in sorted(contest.questions, key=lambda x: x.order)
        ],
    }


@api.post("/contests/{contest_id}/submit")
async def submit_contest(
    contest_id: int,
    payload: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008 — starlette Request is injected
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")
    await _require_subscribed(db, user.telegram_id)

    contest = await db.get(Contest, contest_id)
    if not contest or not contest.is_active:
        raise HTTPException(404, "Yutuqli test topilmadi")

    now = _contest_now()
    state = _contest_state(contest, now)
    if state in ("upcoming", "finished", "inactive"):
        raise HTTPException(400, "Test hozir yechish uchun ochiq emas")

    r = await db.execute(
        select(ContestAttempt).where(
            ContestAttempt.contest_id == contest_id, ContestAttempt.user_id == user.id
        )
    )
    if r.scalar_one_or_none():
        raise HTTPException(400, "Siz allaqachon ishtirok etgansiz")

    answers: dict = payload.get("answers", {})
    time_taken = int(payload.get("time_taken_seconds") or 0)
    if time_taken <= 0 or time_taken > contest.time_limit_seconds:
        time_taken = contest.time_limit_seconds

    score = 0
    total = len(contest.questions)
    for q in contest.questions:
        chosen = answers.get(str(q.id))
        if chosen and chosen == q.correct_option.value:
            score += 1

    attempt = ContestAttempt(
        user_id=user.id,
        contest_id=contest_id,
        score=score,
        total=total,
        time_taken_seconds=time_taken,
        answers=answers,
        completed_at=datetime.now(TASHKENT_TZ),
    )
    db.add(attempt)
    await db.commit()

    return {
        "score": score,
        "total": total,
        "percentage": round(score / total * 100) if total else 0,
        "time_taken_seconds": time_taken,
    }


@api.get("/contests/{contest_id}/review")
async def get_contest_review(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_id: int | None = Header(default=None, alias="X-Telegram-Id"),
    request: Request = None,  # noqa: B008
):
    """Contest tugagach ishtirokchining javob tahlili.

    Musobaqa jarayoni davomida to'g'ri javoblarni yashiramiz (aks holda
    ishtirokchilar bir-biriga aytib qo'yishi mumkin). Faqat `end_at` o'tgach
    yoki `is_active=False` bo'lganda tahlil ochiladi.
    """
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Foydalanuvchi aniqlanmadi")

    contest = await db.get(
        Contest, contest_id, options=[selectinload(Contest.questions)]
    )
    if not contest:
        raise HTTPException(404, "Yutuqli test topilmadi")

    state = _contest_state(contest, _contest_now())
    if state not in ("finished", "inactive"):
        raise HTTPException(
            403, "Tahlil faqat musobaqa yakunlangach ochiladi"
        )

    attempt = (
        await db.execute(
            select(ContestAttempt).where(
                ContestAttempt.contest_id == contest_id,
                ContestAttempt.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(404, "Siz bu musobaqada ishtirok etmagansiz")

    user_answers: dict = attempt.answers or {}
    review = []
    for q in sorted(contest.questions, key=lambda x: x.order):
        chosen = user_answers.get(str(q.id))
        correct = q.correct_option.value
        review.append({
            "id": q.id,
            "text": q.text,
            "image_url": q.image_url,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "chosen": chosen,
            "correct": correct,
            "is_correct": chosen == correct,
            "explanation": q.explanation,
        })

    return {
        "contest": {
            "id": contest.id,
            "title": contest.title,
            "end_at": contest.end_at.isoformat(),
        },
        "attempt": {
            "score": attempt.score,
            "total": attempt.total,
            "percentage": attempt.percentage,
            "time_taken_seconds": attempt.time_taken_seconds,
        },
        "review": review,
    }


@api.get("/contests/{contest_id}/winners")
async def get_contest_winners(
    contest_id: int,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    contest = await db.get(Contest, contest_id)
    if not contest:
        raise HTTPException(404, "Yutuqli test topilmadi")

    rows = (
        await db.execute(
            select(ContestAttempt)
            .where(ContestAttempt.contest_id == contest_id)
            .options(selectinload(ContestAttempt.user))
            .order_by(desc(ContestAttempt.score), ContestAttempt.time_taken_seconds)
            .limit(limit)
        )
    ).scalars().all()

    now = _contest_now()
    return {
        "contest": {
            "id": contest.id,
            "title": contest.title,
            "prize": contest.prize,
            "status": _contest_state(contest, now),
            "end_at": contest.end_at.isoformat() if contest.end_at else None,
        },
        "winners": [
            {
                "rank": i + 1,
                "name": (a.user.first_name or a.user.username or f"#{a.user.telegram_id}"),
                "username": a.user.username,
                "score": a.score,
                "total": a.total,
                "percentage": a.percentage,
                "time_taken_seconds": a.time_taken_seconds,
            }
            for i, a in enumerate(rows)
        ],
    }


# ═══ Admin stats (unchanged) ═════════════════════════════════════════

@api.get("/admin-stats")
async def admin_dashboard_stats(db: AsyncSession = Depends(get_db)):
    users     = await db.scalar(select(func.count()).select_from(TelegramUser)) or 0
    quizzes   = await db.scalar(select(func.count()).select_from(Quiz)) or 0
    questions = await db.scalar(select(func.count()).select_from(Question)) or 0
    topics    = await db.scalar(select(func.count()).select_from(Topic)) or 0
    modules   = await db.scalar(select(func.count()).select_from(Module)) or 0
    active_q  = await db.scalar(select(func.count()).select_from(Quiz).where(Quiz.is_active == True)) or 0  # noqa: E712
    active_t  = await db.scalar(select(func.count()).select_from(Topic).where(Topic.is_active == True)) or 0  # noqa: E712
    attempts  = await db.scalar(select(func.count()).select_from(QuizAttempt)) or 0

    result = await db.execute(
        select(QuizAttempt)
        .options(selectinload(QuizAttempt.user), selectinload(QuizAttempt.quiz))
        .order_by(QuizAttempt.createdAt.desc())
        .limit(6)
    )
    recent = result.scalars().all()

    return {
        "users": users, "quizzes": quizzes, "questions": questions,
        "topics": topics, "modules": modules,
        "active_quizzes": active_q, "active_topics": active_t,
        "total_attempts": attempts,
        "recent_attempts": [
            {
                "user": a.user.first_name or a.user.username or f"#{a.user.telegram_id}",
                "quiz": a.quiz.title,
                "score": a.score,
                "total": a.total,
                "percentage": a.percentage,
                "date": _fmt_tashkent(a.completed_at, "—"),
            }
            for a in recent
        ],
    }


# ═══ My orders ═══════════════════════════════════════════════════════════

_ORDER_STATUS_LABELS = {
    "pending": "To'lov kutilmoqda",
    "confirmed": "To'lov tasdiqlandi",
    "processing": "Manzil qabul qilindi",
    "shipped": "Yo'lda",
}


@api.get("/my-orders")
async def my_orders(
    x_init_data: str | None = Header(None),
    x_tg_id: int | None = Header(None),
    db: AsyncSession = Depends(get_db),
    request: Request = None,  # noqa: B008
):
    user = await _resolve_user(db, x_init_data, x_tg_id, request)
    if not user:
        raise HTTPException(401, "Autentifikatsiya talab etiladi")

    rows = (
        await db.execute(
            select(BookOrder)
            .where(BookOrder.user_id == user.id)
            .options(selectinload(BookOrder.book))
            .order_by(BookOrder.createdAt.desc())
        )
    ).scalars().all()

    return [
        {
            "id": o.id,
            "book_title": o.book.title if o.book else "—",
            "book_price": o.book.price if o.book else 0,
            "status": o.status.value,
            "status_label": _ORDER_STATUS_LABELS.get(o.status.value, o.status.value),
            "delivery_name": o.delivery_name,
            "delivery_phone": o.delivery_phone,
            "delivery_address": o.delivery_address,
            "created_at": _fmt_tashkent(o.createdAt, "—"),
        }
        for o in rows
    ]
