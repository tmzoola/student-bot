"""T-207 uchun quiz submit endpoint smoke."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from models.attempt import QuizAttempt
from models.faculty import Faculty
from models.question import CorrectOption, Question
from models.quiz import Quiz
from models.student_profile import StudentProfile
from models.subject import Subject
from models.telegram_user import TelegramUser
from models.topic import Topic


@pytest_asyncio.fixture
async def seeded(db):
    faculty = Faculty(name="F", code="F1")
    user = TelegramUser(telegram_id=555, first_name="U")
    db.add_all([faculty, user])
    await db.commit()
    await db.refresh(faculty); await db.refresh(user)

    profile = StudentProfile(
        telegram_user_id=user.id, student_id_number="Q-1",
        full_name="Test", faculty_id=faculty.id, course_number=1, semester=1,
        is_approved=True,
    )
    subject = Subject(faculty_id=faculty.id, name="Matematika", code="MATH",
                      course_number=1, semester=1, is_active=True)
    db.add_all([profile, subject])
    await db.commit()
    await db.refresh(profile); await db.refresh(subject)

    topic = Topic(subject_id=subject.id, title="T", order=0, is_active=True)
    db.add(topic); await db.commit(); await db.refresh(topic)

    quiz = Quiz(topic_id=topic.id, title="Test-1", time_limit_seconds=60, is_active=True)
    db.add(quiz); await db.commit(); await db.refresh(quiz)

    q1 = Question(quiz_id=quiz.id, text="1+1?", option_a="1", option_b="2",
                  option_c="3", option_d="4", correct_option=CorrectOption.B, order=0)
    q2 = Question(quiz_id=quiz.id, text="2*2?", option_a="2", option_b="3",
                  option_c="4", option_d="5", correct_option=CorrectOption.C, order=1)
    db.add_all([q1, q2]); await db.commit()
    await db.refresh(q1); await db.refresh(q2)

    return {"profile": profile, "quiz": quiz, "questions": [q1, q2]}


@pytest_asyncio.fixture
async def client(session_factory, seeded):
    from api.v1.student import get_current_profile
    from main import app

    async def _override():
        return seeded["profile"]

    # Override `get_db` ham SQLite factory'ga.
    from db.session import get_db as real_get_db

    async def _override_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_current_profile] = _override
    app.dependency_overrides[real_get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submit_scores_correctly(client, seeded, db):
    q1, q2 = seeded["questions"]
    r = await client.post(
        f"/api/v1/quiz/{seeded['quiz'].id}/submit",
        json={"answers": {str(q1.id): "B", str(q2.id): "A"}, "time_taken_seconds": 42},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["score"] == 1
    assert data["total"] == 2
    assert data["percentage"] == 50

    # Attempt DB'da yozilgan
    attempt = await db.scalar(select(QuizAttempt).where(QuizAttempt.id == data["attempt_id"]))
    assert attempt is not None
    assert attempt.student_profile_id == seeded["profile"].id
    assert attempt.time_taken_seconds == 42


@pytest.mark.asyncio
async def test_get_quiz_hides_correct_option(client, seeded):
    r = await client.get(f"/api/v1/quiz/{seeded['quiz'].id}")
    assert r.status_code == 200
    data = r.json()
    for q in data["questions"]:
        assert "correct_option" not in q
