"""T-510 · Generated quiz submit endpoint (score, 403 begona profil)."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from models.faculty import Faculty
from models.generated_question import GeneratedQuestion
from models.generated_quiz import GeneratedQuiz, QuizDifficulty
from models.material import Material, MaterialStatus
from models.question import CorrectOption
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser


@pytest_asyncio.fixture
async def seeded(db):
    faculty = Faculty(name="F", code="F1")
    u1 = TelegramUser(telegram_id=1001, first_name="A")
    u2 = TelegramUser(telegram_id=1002, first_name="B")
    db.add_all([faculty, u1, u2])
    await db.commit()
    for u in (u1, u2):
        await db.refresh(u)
    await db.refresh(faculty)

    p1 = StudentProfile(
        telegram_user_id=u1.id, student_id_number="P-1",
        full_name="Owner", faculty_id=faculty.id,
        course_number=1, semester=1, is_approved=True,
    )
    p2 = StudentProfile(
        telegram_user_id=u2.id, student_id_number="P-2",
        full_name="Stranger", faculty_id=faculty.id,
        course_number=1, semester=1, is_approved=True,
    )
    db.add_all([p1, p2])
    await db.commit()
    await db.refresh(p1); await db.refresh(p2)

    material = Material(
        student_profile_id=p1.id, title="M", filename="m.txt",
        mime="text/plain", size_bytes=1, storage_path="/tmp/m.txt",
        status=MaterialStatus.ready,
    )
    db.add(material); await db.commit(); await db.refresh(material)

    quiz = GeneratedQuiz(
        material_id=material.id, student_profile_id=p1.id,
        title="AI Q", difficulty=QuizDifficulty.medium,
        language="uz", num_questions=2,
    )
    db.add(quiz); await db.commit(); await db.refresh(quiz)

    q1 = GeneratedQuestion(
        generated_quiz_id=quiz.id, order=0, text="Q1?",
        option_a="a", option_b="b", option_c="c", option_d="d",
        correct_option=CorrectOption.B, explanation="B chunki...",
    )
    q2 = GeneratedQuestion(
        generated_quiz_id=quiz.id, order=1, text="Q2?",
        option_a="a", option_b="b", option_c="c", option_d="d",
        correct_option=CorrectOption.A, explanation=None,
    )
    db.add_all([q1, q2])
    await db.commit()
    await db.refresh(q1); await db.refresh(q2)

    return {"owner": p1, "stranger": p2, "quiz": quiz, "questions": [q1, q2]}


def _mk_client(session_factory, current_profile):
    from api.v1.student import get_current_profile
    from db.session import get_db as real_get_db
    from main import app

    async def _override():
        return current_profile

    async def _override_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_current_profile] = _override
    app.dependency_overrides[real_get_db] = _override_db
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_generated_submit_scores_correctly(session_factory, seeded):
    q1, q2 = seeded["questions"]
    from main import app
    async with _mk_client(session_factory, seeded["owner"]) as client:
        r = await client.post(
            f"/api/v1/generated-quiz/{seeded['quiz'].id}/submit",
            json={"answers": {str(q1.id): "B", str(q2.id): "B"}, "time_taken_seconds": 12},
        )
    app.dependency_overrides.clear()
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["score"] == 1
    assert data["total"] == 2
    assert data["percentage"] == 50
    assert len(data["results"]) == 2
    # Har savol uchun to'g'ri variant qaytadi
    for res in data["results"]:
        assert res["correct_option"] in {"A", "B", "C", "D"}


@pytest.mark.asyncio
async def test_generated_get_hides_correct_option(session_factory, seeded):
    from main import app
    async with _mk_client(session_factory, seeded["owner"]) as client:
        r = await client.get(f"/api/v1/generated-quiz/{seeded['quiz'].id}")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    data = r.json()
    for q in data["questions"]:
        assert "correct_option" not in q
        assert "explanation" not in q


@pytest.mark.asyncio
async def test_generated_submit_403_for_stranger(session_factory, seeded):
    from main import app
    async with _mk_client(session_factory, seeded["stranger"]) as client:
        r = await client.post(
            f"/api/v1/generated-quiz/{seeded['quiz'].id}/submit",
            json={"answers": {}, "time_taken_seconds": 0},
        )
    app.dependency_overrides.clear()
    assert r.status_code == 403
