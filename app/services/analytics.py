"""Admin panel uchun analitika query'lari.

Natijalar Redis'da 1 soat keshlanadi — og'ir joinlar har so'rovda qaytadan
bajarilmasin. Redis yo'q bo'lsa kesh o'chirilgan hisoblanadi (graceful fallback).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.attempt import QuizAttempt
from models.faculty import Faculty
from models.generated_attempt import GeneratedQuizAttempt
from models.generated_quiz import GeneratedQuiz
from models.material import Material
from models.quiz import Quiz
from models.student_profile import StudentProfile
from models.subject import Subject
from models.topic import Topic

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Tashkent")
_CACHE_KEY = "analytics:dashboard"
_CACHE_TTL = 3600  # 1 soat


async def _get_redis():
    try:
        from api.v1.webapp import _redis
        return _redis
    except Exception:  # noqa: BLE001
        return None


async def _cached_get() -> dict | None:
    redis = await _get_redis()
    if redis is None:
        return None
    try:
        raw = await redis.get(_CACHE_KEY)
        return json.loads(raw) if raw else None
    except Exception:
        logger.exception("analytics cache GET xatosi")
        return None


async def _cached_set(data: dict) -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        await redis.set(_CACHE_KEY, json.dumps(data, ensure_ascii=False, default=str), ex=_CACHE_TTL)
    except Exception:
        logger.exception("analytics cache SET xatosi")


async def invalidate_analytics_cache() -> None:
    redis = await _get_redis()
    if redis is None:
        return
    try:
        await redis.delete(_CACHE_KEY)
    except Exception:
        pass


async def compute_analytics(session: AsyncSession, force: bool = False) -> dict:
    """Analitikani hisoblaydi. force=True bo'lmasa keshdan qaytaradi."""
    if not force:
        cached = await _cached_get()
        if cached:
            return cached

    now = datetime.now(_TZ)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ── 1. Umumiy ko'rsatkichlar ────────────────────────────────────────
    total_students = (await session.scalar(select(func.count(StudentProfile.id)))) or 0
    approved_students = (await session.scalar(
        select(func.count(StudentProfile.id)).where(StudentProfile.is_approved.is_(True))
    )) or 0

    # DAU — so'nggi 24 soatda kamida 1 ta urinish qilgan talabalar
    dau_q = (
        select(func.count(distinct(QuizAttempt.student_profile_id)))
        .where(QuizAttempt.completed_at >= day_ago)
    )
    dau_g = (
        select(func.count(distinct(GeneratedQuizAttempt.student_profile_id)))
        .where(GeneratedQuizAttempt.completed_at >= day_ago)
    )
    dau = ((await session.scalar(dau_q)) or 0) + ((await session.scalar(dau_g)) or 0)

    # WAU — so'nggi 7 kun
    wau_q = (
        select(func.count(distinct(QuizAttempt.student_profile_id)))
        .where(QuizAttempt.completed_at >= week_ago)
    )
    wau_g = (
        select(func.count(distinct(GeneratedQuizAttempt.student_profile_id)))
        .where(GeneratedQuizAttempt.completed_at >= week_ago)
    )
    wau = ((await session.scalar(wau_q)) or 0) + ((await session.scalar(wau_g)) or 0)

    # Jami urinishlar va o'rtacha ball
    result_row = (await session.execute(
        select(
            func.count(QuizAttempt.id).label("total"),
            func.coalesce(
                func.avg(QuizAttempt.score * 100.0 / func.nullif(QuizAttempt.total, 0)), 0
            ).label("avg_pct"),
        )
    )).one()
    total_attempts = int(result_row.total)
    avg_percentage = round(float(result_row.avg_pct), 1)

    # ── 2. Ro'yxatdan o'tishlar dinamikasi (oxirgi 30 kun) ─────────────
    reg_rows = (await session.execute(
        select(
            func.date(StudentProfile.createdAt).label("d"),
            func.count(StudentProfile.id).label("cnt"),
        )
        .where(StudentProfile.createdAt >= month_ago)
        .group_by(func.date(StudentProfile.createdAt))
        .order_by(func.date(StudentProfile.createdAt))
    )).all()
    registrations = [{"date": str(r.d), "count": r.cnt} for r in reg_rows]

    # Kunlik urinishlar (oxirgi 30 kun)
    att_rows = (await session.execute(
        select(
            func.date(QuizAttempt.completed_at).label("d"),
            func.count(QuizAttempt.id).label("cnt"),
        )
        .where(QuizAttempt.completed_at >= month_ago)
        .group_by(func.date(QuizAttempt.completed_at))
        .order_by(func.date(QuizAttempt.completed_at))
    )).all()
    daily_attempts = [{"date": str(r.d), "count": r.cnt} for r in att_rows]

    # ── 3. Fakultet va fan bo'yicha foydalanish ─────────────────────────
    fac_rows = (await session.execute(
        select(
            Faculty.name.label("faculty"),
            func.count(QuizAttempt.id).label("attempts"),
        )
        .join(Subject, Subject.faculty_id == Faculty.id)
        .join(Topic, Topic.subject_id == Subject.id)
        .join(Quiz, Quiz.topic_id == Topic.id)
        .join(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .group_by(Faculty.id, Faculty.name)
        .order_by(func.count(QuizAttempt.id).desc())
    )).all()
    top_faculties = [{"faculty": r.faculty, "attempts": r.attempts} for r in fac_rows]

    subj_rows = (await session.execute(
        select(
            Subject.name.label("subject"),
            Faculty.name.label("faculty"),
            func.count(QuizAttempt.id).label("attempts"),
        )
        .join(Topic, Topic.subject_id == Subject.id)
        .join(Quiz, Quiz.topic_id == Topic.id)
        .join(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .join(Faculty, Faculty.id == Subject.faculty_id)
        .group_by(Subject.id, Subject.name, Faculty.name)
        .order_by(func.count(QuizAttempt.id).desc())
        .limit(10)
    )).all()
    top_subjects = [{"subject": r.subject, "faculty": r.faculty, "attempts": r.attempts} for r in subj_rows]

    # ── 4. AI-xususiyat statistikasi ────────────────────────────────────
    material_uploads = (await session.scalar(select(func.count(Material.id)))) or 0
    quizzes_generated = (await session.scalar(select(func.count(GeneratedQuiz.id)))) or 0
    gen_attempts = (await session.scalar(select(func.count(GeneratedQuizAttempt.id)))) or 0

    # Bugungi Claude so'rovlari (GeneratedQuiz + taxminiy) — rough estimate
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_gen = (await session.scalar(
        select(func.count(GeneratedQuiz.id)).where(GeneratedQuiz.createdAt >= today_start)
    )) or 0

    # ── 5. Zaif mavzular (min 3 ta urinish bo'lgan) ─────────────────────
    weak_rows = (await session.execute(
        select(
            Topic.title.label("topic"),
            Subject.name.label("subject"),
            func.round(
                func.avg(QuizAttempt.score * 100.0 / func.nullif(QuizAttempt.total, 0)), 1
            ).label("avg_pct"),
            func.count(QuizAttempt.id).label("cnt"),
        )
        .join(Quiz, Quiz.topic_id == Topic.id)
        .join(QuizAttempt, QuizAttempt.quiz_id == Quiz.id)
        .join(Subject, Subject.id == Topic.subject_id)
        .where(QuizAttempt.total > 0)
        .group_by(Topic.id, Topic.title, Subject.name)
        .having(func.count(QuizAttempt.id) >= 3)
        .order_by(func.avg(QuizAttempt.score * 100.0 / func.nullif(QuizAttempt.total, 0)))
        .limit(10)
    )).all()
    weak_topics = [
        {
            "topic": r.topic,
            "subject": r.subject,
            "avg_pct": round(float(r.avg_pct or 0), 1),
            "attempts": r.cnt,
        }
        for r in weak_rows
    ]

    data = {
        "generated_at": now.isoformat(),
        "summary": {
            "total_students": total_students,
            "approved_students": approved_students,
            "pending_students": total_students - approved_students,
            "dau": dau,
            "wau": wau,
            "total_attempts": total_attempts,
            "avg_percentage": avg_percentage,
        },
        "registrations": registrations,
        "daily_attempts": daily_attempts,
        "top_faculties": top_faculties,
        "top_subjects": top_subjects,
        "ai_stats": {
            "material_uploads": material_uploads,
            "quizzes_generated": quizzes_generated,
            "gen_attempts": gen_attempts,
            "today_gen_calls": today_gen,
        },
        "weak_topics": weak_topics,
    }

    await _cached_set(data)
    return data
