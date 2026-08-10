"""Admin panel yordamchi endpoint'lari."""
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin-tools", tags=["admin-tools"])
templates = Jinja2Templates(directory="templates")


@router.get("/analytics", response_class=HTMLResponse)
async def admin_analytics_page(request: Request):
    return templates.TemplateResponse("admin_analytics.html", {"request": request})


@router.get("/analytics/data")
async def admin_analytics_data(refresh: bool = Query(default=False)):
    """Analitika JSON-i (Redis'da 1 soat keshlanadi).

    ?refresh=true qo'shilsa keshni o'chirib qayta hisoblaydi.
    """
    from db.session import session_factory
    from services.analytics import compute_analytics, invalidate_analytics_cache

    if refresh:
        await invalidate_analytics_cache()

    async with session_factory() as session:
        data = await compute_analytics(session, force=refresh)

    return JSONResponse(content=data)


@router.get("/leaderboard", response_class=HTMLResponse)
async def admin_leaderboard_page(request: Request):
    return templates.TemplateResponse("admin_leaderboard.html", {"request": request})


@router.get("/builder", response_class=HTMLResponse)
async def admin_builder_page(request: Request):
    return templates.TemplateResponse("admin_builder.html", {"request": request})


@router.get("/quiz-import", response_class=HTMLResponse)
async def admin_quiz_import_page(request: Request):
    return templates.TemplateResponse("admin_quiz_import.html", {"request": request})


# ─── T-306 · Talaba tahlili (read-only) ─────────────────────────────

@router.get("/insight/{profile_id}", response_class=HTMLResponse)
async def admin_insight_view(request: Request, profile_id: int):
    """Adminlar uchun talaba statistikasi va keshdagi AI insight'ni ko'rsatish.

    Bu sahifa faqat starlette-admin session'i orqali ochilishi ko'zda tutilgan
    (odatda /admin/ orqali). AI ni bu yerdan chaqirmaymiz — faqat keshdan.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from db.session import session_factory
    from models.student_profile import StudentProfile
    from services.insights.cache import get_cached_insight
    from services.insights.stats import compute_user_stats

    async with session_factory() as session:
        profile = await session.scalar(
            select(StudentProfile)
            .options(selectinload(StudentProfile.faculty))
            .where(StudentProfile.id == profile_id)
        )
        if profile is None:
            return HTMLResponse("<h3>Profil topilmadi</h3>", status_code=404)
        stats = await compute_user_stats(session, profile.id)

    insight = await get_cached_insight(profile.id)
    return templates.TemplateResponse(
        "admin_insight.html",
        {
            "request": request,
            "profile": profile,
            "stats": stats,
            "insight": insight,
        },
    )
