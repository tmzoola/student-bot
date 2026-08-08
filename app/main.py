import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from admin import setup_admin
from api.v1.admin_tools import router as admin_tools_router
from api.v1.webapp import api as webapp_api
from api.v1.webapp import pages as webapp_pages
from core.config import MEDIA_ROOT, settings
from core.error_handlers import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from core.exceptions import AppException
from db.session import session_factory
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from logging_config import setup_logging
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    setup_admin(app)

    # NB: Bot polling + reengagement + pending_joins loop'lari endi alohida
    # `bot` konteynerida (`app/bot_main.py`) ishlaydi. WebApp uvicorn ko'p
    # worker bilan ishlaganda `TelegramConflictError` yuz bermasligi va
    # background task'lar N marta takrorlanmasligi uchun.
    # `bot` obyektining o'zi bu process'da import qilinadi va send_message /
    # get_chat_member kabi chaqiruvlar uchun ishlatiladi.
    logger.info("✅ WebApp lifespan boshlandi (bot polling alohida konteynerda)")

    yield

    logger.info("🔴 WebApp lifespan yakunlandi")
    from bot.setup import bot

    try:
        await bot.session.close()
    except Exception:
        logger.exception("bot.session.close xatosi")


app = FastAPI(
    title="Muslima Darmonova",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    version="1.0.0",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS.split(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_https_deployment = settings.WEBAPP_URL.startswith("https://")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    same_site="none" if _https_deployment else "lax",
    https_only=_https_deployment,
    max_age=60 * 60 * 24 * 30,
)


@app.middleware("http")
async def https_proxy_middleware(request: Request, call_next):
    """
    Behind a TLS-terminating reverse proxy the app receives plain HTTP, so
    url_for()/redirects (e.g. starlette-admin's static assets and the login
    form action) come out as http:// and get blocked as mixed content on an
    https page. When the deployment is https (proxy header, request scheme, or
    an https WEBAPP_URL), rewrite the request scheme (and host) to https so all
    generated URLs are https, and set a CSP with `upgrade-insecure-requests` as
    a browser-side safety net.
    """
    forwarded_proto = request.headers.get("x-forwarded-proto")
    # The public deployment is HTTPS whenever the proxy says so, the request is
    # already https, or WEBAPP_URL is configured as https. The last case covers
    # proxies that terminate TLS but forget to send X-Forwarded-Proto: https.
    https_deploy = (
        forwarded_proto == "https"
        or request.url.scheme == "https"
        or settings.WEBAPP_URL.startswith("https://")
    )

    if https_deploy and request.url.scheme != "https":
        scope = dict(request.scope)
        scope["scheme"] = "https"
        forwarded_host = request.headers.get("x-forwarded-host")
        if forwarded_host:
            scope["headers"] = [
                (b"host", forwarded_host.encode()),
                *[(k, v) for k, v in request.scope["headers"] if k != b"host"],
            ]
        request = Request(scope, request.receive)

    response = await call_next(request)

    if https_deploy:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "upgrade-insecure-requests; "
            "default-src 'self' https: http:; "
            "script-src 'self' https: 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' https: 'unsafe-inline'; "
            "style-src-elem 'self' https: 'unsafe-inline'; "
            "img-src 'self' https: data: blob:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https: http:; "
            "frame-ancestors 'self';"
        )

    return response


# Routes
app.include_router(webapp_pages)
app.include_router(webapp_api)
app.include_router(admin_tools_router)

# User-uploaded media (book files served via endpoint; question images via /media).
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")

# Bundled static assets (landing photo, etc.) — baked into the image.
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
async def health_check():
    """Butun stack diagnostikasi bitta joyda.
    UptimeRobot va admin uchun — DB, Redis, pool holati.
    """
    import time as _t
    from db.session import engine as _engine

    result: dict = {"status": "ok"}
    overall_ok = True

    # DB latency + ping
    t0 = _t.perf_counter()
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_latency_ms = int((_t.perf_counter() - t0) * 1000)
        result["db"] = {"ok": True, "latency_ms": db_latency_ms}
    except Exception as e:
        logger.error("Health: DB error: %s", e)
        result["db"] = {"ok": False, "error": str(e)[:120]}
        overall_ok = False

    # SQLAlchemy pool holati (real vaqtda qancha ulanish band)
    try:
        pool = _engine.pool
        result["pool"] = {
            "size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }
    except Exception:
        pass

    # Redis ping
    try:
        from api.v1.webapp import _redis  # local import — circular xavfsizligi uchun

        if _redis is not None:
            t1 = _t.perf_counter()
            pong = await _redis.ping()
            redis_latency_ms = int((_t.perf_counter() - t1) * 1000)
            result["redis"] = {"ok": bool(pong), "latency_ms": redis_latency_ms}
        else:
            result["redis"] = {"ok": False, "error": "client not initialized"}
    except Exception as e:
        logger.warning("Health: Redis error: %s", e)
        result["redis"] = {"ok": False, "error": str(e)[:120]}
        # Redis muhim, lekin butun stack'ni yiqitmaymiz — WebApp Redis'siz ham
        # ishlaydi (in-memory fallback yo'q, lekin subscription kesh o'chadi).

    if not overall_ok:
        return JSONResponse(status_code=503, content=result)
    return result


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
