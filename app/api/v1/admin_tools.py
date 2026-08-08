"""Admin panel yordamchi endpoint'lari.

Refaktor bosqichi: T-102 doirasida kitob/do'kon/broadcast/quote/menu bilan
bog'liq legacy endpoint'lar olib tashlandi. Faqat leaderboard va quiz-import
kabi asosiy sahifalar qoldi. Student-bot uchun admin qismini keyingi
bosqichlarda qayta yozamiz.
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin-tools", tags=["admin-tools"])
templates = Jinja2Templates(directory="templates")


@router.get("/leaderboard", response_class=HTMLResponse)
async def admin_leaderboard_page(request: Request):
    return templates.TemplateResponse("admin_leaderboard.html", {"request": request})


@router.get("/builder", response_class=HTMLResponse)
async def admin_builder_page(request: Request):
    return templates.TemplateResponse("admin_builder.html", {"request": request})


@router.get("/quiz-import", response_class=HTMLResponse)
async def admin_quiz_import_page(request: Request):
    return templates.TemplateResponse("admin_quiz_import.html", {"request": request})
