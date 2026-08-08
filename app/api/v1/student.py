"""Student WebApp uchun HTML sahifalar va JSON API.

Barcha endpoint'lar `X-Init-Data` header'i orqali Telegram initData'ni
tekshiradi. Foydalanuvchi profili topilmasa yoki tasdiqlanmagan bo'lsa 403.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.session import get_db
from models.attempt import QuizAttempt
from models.faculty import Faculty
from models.question import CorrectOption, Question
from models.quiz import Quiz
from models.student_profile import StudentProfile
from models.subject import Subject
from models.telegram_user import TelegramUser
from models.topic import Topic
from utils.webapp_auth import extract_telegram_id

logger = logging.getLogger(__name__)

_TZ = ZoneInfo("Asia/Tashkent")

pages = APIRouter(tags=["student-pages"])
api = APIRouter(prefix="/api/v1", tags=["student-api"])

templates = Jinja2Templates(directory="templates")


# ─── Auth dependency ─────────────────────────────────────────────────

async def get_current_profile(
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
    db: AsyncSession = Depends(get_db),
) -> StudentProfile:
    if not x_init_data:
        raise HTTPException(status_code=401, detail="initData yo'q")
    telegram_id = extract_telegram_id(x_init_data)
    if telegram_id is None:
        raise HTTPException(status_code=401, detail="initData yaroqsiz")
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
    return templates.TemplateResponse("subjects.html", {"request": request})


@pages.get("/subjects/{subject_id}", response_class=HTMLResponse)
async def subject_detail_page(request: Request, subject_id: int):
    return templates.TemplateResponse(
        "subject_detail.html", {"request": request, "subject_id": subject_id}
    )


@pages.get("/quiz/{quiz_id}", response_class=HTMLResponse)
async def quiz_page(request: Request, quiz_id: int):
    return templates.TemplateResponse("quiz.html", {"request": request, "quiz_id": quiz_id})


@pages.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})


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


# Faculty import shu joyda ishlatilmasligi ilova import'ni sinaydi.
_ = Faculty
_ = Question
