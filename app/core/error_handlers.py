import logging
import traceback

from core.exceptions import AppException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from schemas.error import ErrorResponse, ValidationErrorResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status_code=exc.status_code, error=exc.error, detail=exc.detail
        ).model_dump(),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": " -> ".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(
            status_code=422, error="ValidationError", detail=errors
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # `exc.detail` — Foydalanuvchiga ko'rsatiladigan matn (yoki dict). Frontendlar
    # `detail` maydonini ochib o'qiydi, shu sababli uni matn shaklida qaytaramiz.
    if isinstance(exc.detail, str):
        message = exc.detail
    else:
        # HTTPException(detail={"code": ..., "missing_chats": [...]}) kabi holatlar
        # uchun dict'ni JSON string sifatida uzatib, frontend parse qila oladi.
        import json as _json
        try:
            message = _json.dumps(exc.detail, ensure_ascii=False)
        except Exception:
            message = str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status_code=exc.status_code, error="HTTPError", detail=message
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    logger.exception(f"Unhandled exception at {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            status_code=500,
            error="Internal server error",
            detail="InternalServerError",
        ).model_dump(),
    )
