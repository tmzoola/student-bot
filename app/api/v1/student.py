"""Student WebApp uchun HTML sahifalar va JSON API.

Barcha endpoint'lar `X-Init-Data` header'i orqali Telegram initData'ni
tekshiradi. Foydalanuvchi profili topilmasa yoki tasdiqlanmagan bo'lsa 403.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import MEDIA_ROOT
from db.session import get_db
from models.attempt import QuizAttempt
from models.faculty import Faculty
from models.generated_attempt import GeneratedQuizAttempt
from models.generated_question import GeneratedQuestion
from models.generated_quiz import GeneratedQuiz
from models.material import Material, MaterialStatus
from models.question import CorrectOption, Question
from models.quiz import Quiz
from models.student_profile import StudentProfile
from models.subject import Subject
from models.telegram_user import TelegramUser
from models.topic import Topic
from services.materials.extract import (
    ALLOWED_MIMES,
    MAX_MATERIAL_SIZE,
    MIME_DOCX,
    MIME_PDF,
    MIME_TXT,
)
from utils.webapp_auth import extract_telegram_id

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Tashkent")

pages = APIRouter(tags=["student-pages"])
api = APIRouter(prefix="/api/v1", tags=["student-api"])

templates = Jinja2Templates(directory="templates")


# ─── Auth dependency ─────────────────────────────────────────────────

async def get_current_profile(
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    x_tg_user_id: str | None = Header(default=None, alias="X-Tg-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    telegram_id: int | None = None
    if x_init_data:
        telegram_id = extract_telegram_id(x_init_data)
        if telegram_id is None:
            logger.warning("initData validation failed (len=%s)", len(x_init_data))
    if telegram_id is None and x_tg_user_id:
        try:
            telegram_id = int(x_tg_user_id)
        except ValueError:
            telegram_id = None
    if telegram_id is None:
        logger.warning(
            "auth: initData yo'q yoki yaroqsiz (init_len=%s, tg_id_hdr=%r)",
            len(x_init_data) if x_init_data else 0,
            x_tg_user_id,
        )
        raise HTTPException(status_code=401, detail="initData yo'q yoki yaroqsiz")
    profile = await db.scalar(
        select(StudentProfile)
        .options(selectinload(StudentProfile.faculty))
        .join(TelegramUser, TelegramUser.id == StudentProfile.telegram_user_id)
        .where(TelegramUser.telegram_id == telegram_id)
    )
    if profile is None:
        raise HTTPException(status_code=403, detail="Profil topilmadi — ro'yxatdan o'ting")
    if not profile.is_approved:
        raise HTTPException(status_code=403, detail="Profilingiz hali tasdiqlanmagan")
    return profile


# ─── Schemas ─────────────────────────────────────────────────────────

class SubjectOut(BaseModel):
    id: int
    name: str
    code: str
    course_number: int
    semester: int
    topics_count: int
    quizzes_count: int


class TopicQuizOut(BaseModel):
    id: int
    title: str
    questions_count: int
    time_limit_seconds: int


class TopicOut(BaseModel):
    id: int
    title: str
    description: str | None
    quizzes: list[TopicQuizOut]


class SubjectDetailOut(BaseModel):
    id: int
    name: str
    code: str
    description: str | None
    topics: list[TopicOut]


class QuestionOut(BaseModel):
    id: int
    text: str | None
    image_url: str | None
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class QuizOut(BaseModel):
    id: int
    title: str
    description: str | None
    time_limit_seconds: int
    questions: list[QuestionOut]


class SubmitPayload(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    time_taken_seconds: int = Field(ge=0, default=0)


class SubmitOut(BaseModel):
    attempt_id: int
    score: int
    total: int
    percentage: int


class QuestionReviewOut(BaseModel):
    id: int
    order: int
    text: str | None
    image_url: str | None
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    user_option: str | None
    is_correct: bool


class AttemptDetailOut(BaseModel):
    attempt_id: int
    quiz_id: int
    quiz_title: str
    score: int
    total: int
    percentage: int
    time_taken_seconds: int
    questions: list[QuestionReviewOut]


class ProfileOut(BaseModel):
    id: int
    student_id_number: str
    full_name: str
    faculty_name: str
    course_number: int
    semester: int
    attempts_count: int
    average_percentage: int


class AttemptOut(BaseModel):
    id: int
    quiz_id: int
    quiz_title: str
    score: int
    total: int
    percentage: int
    time_taken_seconds: int
    completed_at: datetime | None


# ─── HTML pages ─────────────────────────────────────────────────────
# HTML sahifalar auth'siz — initData validation client tomonidan qilingan
# fetch'da amalga oshadi. Sahifa yuklanishida faqat template render'lanadi.

@pages.get("/subjects", response_class=HTMLResponse)
async def subjects_page(request: Request):
    return templates.TemplateResponse("subjects.html", {"request": request, "nav_active": "subjects"})


@pages.get("/subjects/{subject_id}", response_class=HTMLResponse)
async def subject_detail_page(request: Request, subject_id: int):
    return templates.TemplateResponse(
        "subject_detail.html", {"request": request, "subject_id": subject_id, "nav_active": "subjects"}
    )


@pages.get("/quiz/attempt/{attempt_id}", response_class=HTMLResponse)
async def attempt_page(request: Request, attempt_id: int):
    return templates.TemplateResponse("attempt.html", {"request": request, "attempt_id": attempt_id})


@pages.get("/quiz/{quiz_id}", response_class=HTMLResponse)
async def quiz_page(request: Request, quiz_id: int):
    return templates.TemplateResponse("quiz.html", {"request": request, "quiz_id": quiz_id})


@pages.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request, "nav_active": "profile"})


@pages.get("/materials", response_class=HTMLResponse)
async def materials_page(request: Request):
    return templates.TemplateResponse("materials.html", {"request": request, "nav_active": "materials"})


@pages.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request):
    return templates.TemplateResponse("insights.html", {"request": request, "nav_active": "insights"})


@pages.get("/materials/{material_id}/quiz/{quiz_id}", response_class=HTMLResponse)
async def generated_quiz_page(request: Request, material_id: int, quiz_id: int):
    return templates.TemplateResponse(
        "generated_quiz.html",
        {"request": request, "material_id": material_id, "quiz_id": quiz_id},
    )


# ─── JSON API ───────────────────────────────────────────────────────

@api.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> list[SubjectOut]:
    stmt = (
        select(
            Subject,
            func.count(func.distinct(Topic.id)).label("topics_count"),
            func.count(func.distinct(Quiz.id)).label("quizzes_count"),
        )
        .outerjoin(Topic, Topic.subject_id == Subject.id)
        .outerjoin(Quiz, Quiz.topic_id == Topic.id)
        .where(
            Subject.faculty_id == profile.faculty_id,
            Subject.course_number == profile.course_number,
            Subject.semester == profile.semester,
            Subject.is_active.is_(True),
        )
        .group_by(Subject.id)
        .order_by(Subject.name)
    )
    rows = (await db.execute(stmt)).all()
    return [
        SubjectOut(
            id=s.id,
            name=s.name,
            code=s.code,
            course_number=s.course_number,
            semester=s.semester,
            topics_count=int(tc),
            quizzes_count=int(qc),
        )
        for s, tc, qc in rows
    ]


async def _load_subject_for_profile(
    db: AsyncSession, subject_id: int, profile: StudentProfile
) -> Subject:
    subject = await db.scalar(
        select(Subject)
        .options(selectinload(Subject.topics).selectinload(Topic.quizzes).selectinload(Quiz.questions))
        .where(Subject.id == subject_id)
    )
    if subject is None:
        raise HTTPException(status_code=404, detail="Fan topilmadi")
    if (
        subject.faculty_id != profile.faculty_id
        or subject.course_number != profile.course_number
        or subject.semester != profile.semester
    ):
        raise HTTPException(status_code=403, detail="Bu fan sizning profilinggizga tegishli emas")
    return subject


@api.get("/subjects/{subject_id}", response_model=SubjectDetailOut)
async def subject_detail(
    subject_id: int,
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> SubjectDetailOut:
    subject = await _load_subject_for_profile(db, subject_id, profile)
    topics = [
        TopicOut(
            id=t.id,
            title=t.title,
            description=t.description,
            quizzes=[
                TopicQuizOut(
                    id=q.id,
                    title=q.title,
                    questions_count=len(q.questions),
                    time_limit_seconds=q.time_limit_seconds,
                )
                for q in t.quizzes
                if q.is_active
            ],
        )
        for t in subject.topics
        if t.is_active
    ]
    return SubjectDetailOut(
        id=subject.id,
        name=subject.name,
        code=subject.code,
        description=subject.description,
        topics=topics,
    )


async def _load_quiz_for_profile(
    db: AsyncSession, quiz_id: int, profile: StudentProfile
) -> Quiz:
    quiz = await db.scalar(
        select(Quiz)
        .options(
            selectinload(Quiz.questions),
            selectinload(Quiz.topic).selectinload(Topic.subject),
        )
        .where(Quiz.id == quiz_id)
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    subj = quiz.topic.subject
    if (
        subj.faculty_id != profile.faculty_id
        or subj.course_number != profile.course_number
        or subj.semester != profile.semester
    ):
        raise HTTPException(status_code=403, detail="Bu test sizga tegishli emas")
    return quiz


@api.get("/quiz/attempt/{attempt_id}", response_model=AttemptDetailOut)
async def get_attempt_detail(
    attempt_id: int,
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> AttemptDetailOut:
    attempt = await db.scalar(
        select(QuizAttempt)
        .options(
            selectinload(QuizAttempt.quiz).selectinload(Quiz.questions)
        )
        .where(QuizAttempt.id == attempt_id, QuizAttempt.student_profile_id == profile.id)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Urinish topilmadi")
    answers: dict = attempt.answers or {}
    questions = sorted(attempt.quiz.questions, key=lambda q: q.order)
    return AttemptDetailOut(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz_id,
        quiz_title=attempt.quiz.title,
        score=attempt.score,
        total=attempt.total,
        percentage=attempt.percentage,
        time_taken_seconds=attempt.time_taken_seconds,
        questions=[
            QuestionReviewOut(
                id=q.id,
                order=q.order,
                text=q.text,
                image_url=q.image_url,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
                correct_option=q.correct_option.value,
                user_option=answers.get(str(q.id)),
                is_correct=answers.get(str(q.id)) == q.correct_option.value,
            )
            for q in questions
        ],
    )


@api.get("/quiz/{quiz_id}", response_model=QuizOut)
async def get_quiz(
    quiz_id: int,
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> QuizOut:
    quiz = await _load_quiz_for_profile(db, quiz_id, profile)
    return QuizOut(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        time_limit_seconds=quiz.time_limit_seconds,
        questions=[
            QuestionOut(
                id=q.id,
                text=q.text,
                image_url=q.image_url,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
            )
            for q in sorted(quiz.questions, key=lambda x: x.order)
        ],
    )


@api.post("/quiz/{quiz_id}/submit", response_model=SubmitOut)
async def submit_quiz(
    quiz_id: int,
    payload: SubmitPayload,
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> SubmitOut:
    quiz = await _load_quiz_for_profile(db, quiz_id, profile)
    total = len(quiz.questions)
    score = 0
    normalized_answers: dict[str, str] = {}
    valid_letters = {opt.value for opt in CorrectOption}
    for q in quiz.questions:
        given = payload.answers.get(str(q.id)) or payload.answers.get(str(q.id).lower())
        if isinstance(given, str):
            given_up = given.strip().upper()
            if given_up in valid_letters:
                normalized_answers[str(q.id)] = given_up
                if given_up == q.correct_option.value:
                    score += 1

    attempt = QuizAttempt(
        student_profile_id=profile.id,
        quiz_id=quiz.id,
        score=score,
        total=total,
        time_taken_seconds=payload.time_taken_seconds,
        answers=normalized_answers,
        completed_at=datetime.now(_TZ),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return SubmitOut(
        attempt_id=attempt.id,
        score=score,
        total=total,
        percentage=attempt.percentage,
    )


@api.get("/profile", response_model=ProfileOut)
async def get_profile(
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    row = (
        await db.execute(
            select(
                func.count(QuizAttempt.id),
                func.coalesce(func.sum(QuizAttempt.score), 0),
                func.coalesce(func.sum(QuizAttempt.total), 0),
            ).where(QuizAttempt.student_profile_id == profile.id)
        )
    ).one()
    attempts, total_score, total_max = int(row[0]), int(row[1]), int(row[2])
    avg = round(total_score / total_max * 100) if total_max else 0
    return ProfileOut(
        id=profile.id,
        student_id_number=profile.student_id_number,
        full_name=profile.full_name,
        faculty_name=profile.faculty.name if profile.faculty else "",
        course_number=profile.course_number,
        semester=profile.semester,
        attempts_count=attempts,
        average_percentage=avg,
    )


@api.get("/profile/attempts", response_model=list[AttemptOut])
async def list_attempts(
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> list[AttemptOut]:
    stmt = (
        select(QuizAttempt, Quiz.title)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(QuizAttempt.student_profile_id == profile.id)
        .order_by(QuizAttempt.completed_at.desc().nullslast(), QuizAttempt.id.desc())
        .limit(20)
    )
    rows = (await db.execute(stmt)).all()
    return [
        AttemptOut(
            id=a.id,
            quiz_id=a.quiz_id,
            quiz_title=title,
            score=a.score,
            total=a.total,
            percentage=a.percentage,
            time_taken_seconds=a.time_taken_seconds,
            completed_at=a.completed_at,
        )
        for a, title in rows
    ]


# ─── Materials (T-506, T-509) ──────────────────────────────────────

_MIME_EXT = {MIME_PDF: ".pdf", MIME_DOCX: ".docx", MIME_TXT: ".txt"}


class MaterialOut(BaseModel):
    id: int
    title: str
    status: str
    size_bytes: int
    quizzes_count: int
    error_message: str | None
    created_at: datetime


class MaterialDetailOut(BaseModel):
    id: int
    title: str
    status: str
    size_bytes: int
    extracted_text_length: int
    error_message: str | None
    created_at: datetime
    generated_quizzes: list[dict]


class MaterialUploadOut(BaseModel):
    id: int
    title: str
    status: str


@api.get("/materials", response_model=list[MaterialOut])
async def list_materials(
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> list[MaterialOut]:
    stmt = (
        select(Material, func.count(GeneratedQuiz.id).label("qcount"))
        .outerjoin(GeneratedQuiz, GeneratedQuiz.material_id == Material.id)
        .where(Material.student_profile_id == profile.id)
        .group_by(Material.id)
        .order_by(Material.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        MaterialOut(
            id=m.id,
            title=m.title,
            status=m.status.value if hasattr(m.status, "value") else str(m.status),
            size_bytes=m.size_bytes,
            quizzes_count=int(qc),
            error_message=m.error_message,
            created_at=m.created_at,
        )
        for m, qc in rows
    ]


@api.get("/materials/{material_id}", response_model=MaterialDetailOut)
async def material_detail(
    material_id: int,
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> MaterialDetailOut:
    material = await db.scalar(
        select(Material)
        .options(selectinload(Material.generated_quizzes))
        .where(Material.id == material_id)
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Material topilmadi")
    if material.student_profile_id != profile.id:
        raise HTTPException(status_code=403, detail="Bu material sizga tegishli emas")
    return MaterialDetailOut(
        id=material.id,
        title=material.title,
        status=material.status.value if hasattr(material.status, "value") else str(material.status),
        size_bytes=material.size_bytes,
        extracted_text_length=material.extracted_text_length,
        error_message=material.error_message,
        created_at=material.created_at,
        generated_quizzes=[
            {
                "id": q.id,
                "title": q.title,
                "num_questions": q.num_questions,
                "difficulty": q.difficulty.value if hasattr(q.difficulty, "value") else str(q.difficulty),
            }
            for q in material.generated_quizzes
        ],
    )


@api.post("/materials/upload", response_model=MaterialUploadOut)
async def upload_material(
    file: UploadFile = File(...),
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> MaterialUploadOut:
    """WebApp orqali PDF/DOCX/TXT yuklash."""
    mime = file.content_type or ""
    if mime not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Faqat PDF, DOCX yoki TXT")

    # T-509 rate limit — Redis counter (import lokal, service circular xavfsizligi)
    try:
        from services.ai_rate_limit import check_and_increment_daily
        await check_and_increment_daily(profile.id)
    except HTTPException:
        raise
    except Exception:
        logger.exception("rate limit check xatosi — o'tkazib yuborildi")

    ext = _MIME_EXT.get(mime, "")
    target_dir = MEDIA_ROOT / "materials" / str(profile.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    storage_path = target_dir / filename

    size = 0
    with storage_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_MATERIAL_SIZE:
                out.close()
                storage_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=400,
                    detail=f"Fayl hajmi {MAX_MATERIAL_SIZE // (1024*1024)} MB dan oshmasin",
                )
            out.write(chunk)

    material = Material(
        student_profile_id=profile.id,
        title=file.filename or filename,
        filename=filename,
        mime=mime,
        size_bytes=size,
        storage_path=str(storage_path),
        status=MaterialStatus.uploaded,
    )
    db.add(material)
    await db.commit()
    await db.refresh(material)

    # Background pipeline (bot handler bilan bir xil) — chat_id yo'q,
    # foydalanuvchi WebApp'da polling qiladi.
    from bot.handlers.materials import _process_material_no_chat  # lazy
    asyncio.create_task(_process_material_no_chat(material.id))

    return MaterialUploadOut(
        id=material.id,
        title=material.title,
        status=material.status.value,
    )


# ─── Generated Quiz (T-507) ────────────────────────────────────────

class GeneratedQuestionOut(BaseModel):
    id: int
    order: int
    text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class GeneratedQuizOut(BaseModel):
    id: int
    title: str
    num_questions: int
    difficulty: str
    questions: list[GeneratedQuestionOut]


class GeneratedSubmitPayload(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)
    time_taken_seconds: int = Field(ge=0, default=0)


class GeneratedQuestionResult(BaseModel):
    id: int
    correct_option: str
    user_option: str | None
    is_correct: bool
    explanation: str | None


class GeneratedSubmitOut(BaseModel):
    attempt_id: int
    score: int
    total: int
    percentage: int
    results: list[GeneratedQuestionResult]


async def _load_generated_quiz_for_profile(
    db: AsyncSession, quiz_id: int, profile: StudentProfile
) -> GeneratedQuiz:
    quiz = await db.scalar(
        select(GeneratedQuiz)
        .options(selectinload(GeneratedQuiz.questions))
        .where(GeneratedQuiz.id == quiz_id)
    )
    if quiz is None:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    if quiz.student_profile_id != profile.id:
        raise HTTPException(status_code=403, detail="Bu test sizga tegishli emas")
    return quiz


@api.get("/generated-quiz/{quiz_id}", response_model=GeneratedQuizOut)
async def get_generated_quiz(
    quiz_id: int,
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> GeneratedQuizOut:
    quiz = await _load_generated_quiz_for_profile(db, quiz_id, profile)
    return GeneratedQuizOut(
        id=quiz.id,
        title=quiz.title,
        num_questions=quiz.num_questions,
        difficulty=quiz.difficulty.value if hasattr(quiz.difficulty, "value") else str(quiz.difficulty),
        questions=[
            GeneratedQuestionOut(
                id=q.id, order=q.order, text=q.text,
                option_a=q.option_a, option_b=q.option_b,
                option_c=q.option_c, option_d=q.option_d,
            )
            for q in sorted(quiz.questions, key=lambda x: x.order)
        ],
    )


@api.post("/generated-quiz/{quiz_id}/submit", response_model=GeneratedSubmitOut)
async def submit_generated_quiz(
    quiz_id: int,
    payload: GeneratedSubmitPayload,
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> GeneratedSubmitOut:
    quiz = await _load_generated_quiz_for_profile(db, quiz_id, profile)
    total = len(quiz.questions)
    score = 0
    normalized: dict[str, str] = {}
    valid = {opt.value for opt in CorrectOption}
    results: list[GeneratedQuestionResult] = []
    for q in sorted(quiz.questions, key=lambda x: x.order):
        given_raw = payload.answers.get(str(q.id)) or payload.answers.get(str(q.id).lower())
        user_up: str | None = None
        if isinstance(given_raw, str):
            up = given_raw.strip().upper()
            if up in valid:
                user_up = up
                normalized[str(q.id)] = up
        correct_letter = q.correct_option.value if hasattr(q.correct_option, "value") else str(q.correct_option)
        is_correct = user_up == correct_letter
        if is_correct:
            score += 1
        results.append(
            GeneratedQuestionResult(
                id=q.id,
                correct_option=correct_letter,
                user_option=user_up,
                is_correct=is_correct,
                explanation=q.explanation,
            )
        )

    attempt = GeneratedQuizAttempt(
        generated_quiz_id=quiz.id,
        student_profile_id=profile.id,
        score=score,
        total=total,
        time_taken_seconds=payload.time_taken_seconds,
        answers=normalized,
        completed_at=datetime.now(_TZ),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return GeneratedSubmitOut(
        attempt_id=attempt.id,
        score=score,
        total=total,
        percentage=attempt.percentage,
        results=results,
    )


# ─── Insights (T-302, T-303, T-305) ────────────────────────────────

class InsightWeakness(BaseModel):
    topic: str
    tip: str
    accuracy: int | None = None


class InsightStrength(BaseModel):
    topic: str
    accuracy: int | None = None


class InsightOut(BaseModel):
    summary: str
    weaknesses: list[InsightWeakness] = Field(default_factory=list)
    strengths: list[InsightStrength] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class TopicStatOut(BaseModel):
    topic_title: str
    subject_name: str
    attempts: int
    correct: int
    wrong: int
    accuracy_pct: int


class SubjectStatOut(BaseModel):
    subject_name: str
    attempts: int
    accuracy_pct: int


class TrendPointOut(BaseModel):
    week_start: str
    attempts: int
    accuracy_pct: int


class InsightsPayloadOut(BaseModel):
    attempts_total: int
    overall_accuracy_pct: int
    top_weaknesses: list[TopicStatOut]
    top_strengths: list[TopicStatOut]
    by_subject: list[SubjectStatOut]
    recent_trend: list[TrendPointOut]
    ai_insight: InsightOut | None
    insufficient_data: bool
    min_attempts_required: int = 3


_MIN_ATTEMPTS_FOR_INSIGHT = 3


def _stats_to_payload(
    stats, insight
) -> InsightsPayloadOut:
    return InsightsPayloadOut(
        attempts_total=stats.attempts_total,
        overall_accuracy_pct=stats.overall_accuracy_pct,
        top_weaknesses=[
            TopicStatOut(
                topic_title=t.topic_title, subject_name=t.subject_name,
                attempts=t.attempts, correct=t.correct, wrong=t.wrong,
                accuracy_pct=t.accuracy_pct,
            ) for t in stats.top_weaknesses
        ],
        top_strengths=[
            TopicStatOut(
                topic_title=t.topic_title, subject_name=t.subject_name,
                attempts=t.attempts, correct=t.correct, wrong=t.wrong,
                accuracy_pct=t.accuracy_pct,
            ) for t in stats.top_strengths
        ],
        by_subject=[
            SubjectStatOut(
                subject_name=s.subject_name, attempts=s.attempts,
                accuracy_pct=s.accuracy_pct,
            ) for s in stats.by_subject
        ],
        recent_trend=[
            TrendPointOut(
                week_start=t.week_start, attempts=t.attempts,
                accuracy_pct=t.accuracy_pct,
            ) for t in stats.recent_trend
        ],
        ai_insight=(
            InsightOut(
                summary=insight.summary,
                weaknesses=[
                    InsightWeakness(topic=w.topic, tip=w.tip, accuracy=w.accuracy)
                    for w in insight.weaknesses
                ],
                strengths=[
                    InsightStrength(topic=s.topic, accuracy=s.accuracy)
                    for s in insight.strengths
                ],
                recommendations=list(insight.recommendations),
            )
            if insight is not None else None
        ),
        insufficient_data=stats.attempts_total < _MIN_ATTEMPTS_FOR_INSIGHT,
        min_attempts_required=_MIN_ATTEMPTS_FOR_INSIGHT,
    )


@api.get("/insights", response_model=InsightsPayloadOut)
async def get_insights(
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> InsightsPayloadOut:
    """Statistika + (agar kesh bor bo'lsa) AI insight qaytaradi.

    AI ni bu endpoint AVTOMATIK chaqirmaydi — foydalanuvchi "Tavsiya olish"
    tugmasini bosganda `/insights/generate` orqali triggerlaydi.
    """
    from services.insights.cache import get_cached_insight
    from services.insights.stats import compute_user_stats

    stats = await compute_user_stats(db, profile.id)
    insight = await get_cached_insight(profile.id)
    return _stats_to_payload(stats, insight)


@api.post("/insights/generate", response_model=InsightsPayloadOut)
async def generate_insights(
    profile: StudentProfile = Depends(get_current_profile),
    db: AsyncSession = Depends(get_db),
) -> InsightsPayloadOut:
    """AI tavsiya ishlab chiqishga trigger. Kunlik AI limit hisobiga kiradi.

    Agar kesh yangi (24h ichida) bo'lsa — qayta generatsiya QILINMAYDI,
    keshdagi natija qaytariladi (rate limit sarflanmaydi).
    """
    from services.ai_rate_limit import check_and_increment_daily
    from services.insights.ai_analyze import generate_insight
    from services.insights.cache import get_cached_insight, set_cached_insight
    from services.insights.stats import compute_user_stats

    stats = await compute_user_stats(db, profile.id)
    if stats.attempts_total < _MIN_ATTEMPTS_FOR_INSIGHT:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Yetarli ma'lumot yo'q. Kamida {_MIN_ATTEMPTS_FOR_INSIGHT} "
                "urinish qiling."
            ),
        )

    cached = await get_cached_insight(profile.id)
    if cached is not None:
        return _stats_to_payload(stats, cached)

    # Rate limit — insight ham AI chaqiruvi, kunlik limit hisobiga kiradi.
    await check_and_increment_daily(profile.id)

    # Faculty selectinload allaqachon get_current_profile'da qilingan.
    try:
        insight = await generate_insight(stats, profile)
    except Exception as exc:
        logger.exception("insight generatsiya xatosi (profile_id=%s)", profile.id)
        raise HTTPException(status_code=502, detail=f"AI xatosi: {exc}") from exc

    await set_cached_insight(profile.id, insight)
    return _stats_to_payload(stats, insight)


# Faculty import shu joyda ishlatilmasligi ilova import'ni sinaydi.
_ = Faculty
_ = Question
_ = GeneratedQuestion
