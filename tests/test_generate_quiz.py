"""T-504 · Material'dan test generatsiya qilish end-to-end (AI mock)."""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select

import db.session as db_session
from models.faculty import Faculty
from models.generated_quiz import QuizDifficulty
from models.material import Material, MaterialStatus
from models.material_chunk import MaterialChunk
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser
from services.ai.base import AIProvider, AIProviderError
from services.ai.schemas import GeneratedQuestionData, QuizGenResult


async def _seed_material(session_factory, *, with_chunks: bool = True) -> int:
    async with session_factory() as s:
        faculty = Faculty(name="F", code=f"F{id(session_factory) & 0xffff}")
        user = TelegramUser(telegram_id=999, first_name="U")
        s.add_all([faculty, user])
        await s.commit()
        profile = StudentProfile(
            telegram_user_id=user.id,
            student_id_number="S-1",
            full_name="Testchi",
            faculty_id=faculty.id,
            course_number=1,
            semester=1,
            is_approved=True,
        )
        s.add(profile)
        await s.commit()
        material = Material(
            student_profile_id=profile.id,
            title="Konspekt",
            filename="konspekt.txt",
            mime="text/plain",
            size_bytes=100,
            storage_path="/tmp/konspekt.txt",
            status=MaterialStatus.uploaded,
        )
        s.add(material)
        await s.commit()
        if with_chunks:
            s.add_all(
                [
                    MaterialChunk(material_id=material.id, order=0, text="Birinchi paragraf matni"),
                    MaterialChunk(material_id=material.id, order=1, text="Ikkinchi paragraf matni"),
                ]
            )
            await s.commit()
        return material.id


def _fake_result(n: int = 3) -> QuizGenResult:
    return QuizGenResult(
        title="AI test — Konspekt",
        questions=[
            GeneratedQuestionData(
                text=f"Savol {i+1}?",
                option_a="A variant",
                option_b="B variant",
                option_c="C variant",
                option_d="D variant",
                correct_option="B",
                explanation="Chunki B to'g'ri.",
            )
            for i in range(n)
        ],
        input_tokens=100,
        output_tokens=200,
    )


@pytest.mark.asyncio
async def test_generate_quiz_happy_path(session_factory, monkeypatch):
    material_id = await _seed_material(session_factory, with_chunks=True)

    from services.materials import generate as gen_mod

    class _FakeProvider(AIProvider):
        async def generate_quiz(self, text, num_questions=10, difficulty="medium", language="uz"):
            assert "paragraf" in text
            return _fake_result(3)

    monkeypatch.setattr(gen_mod, "get_ai_provider", lambda: _FakeProvider())

    quiz = await gen_mod.generate_quiz_for_material(
        material_id=material_id, num_questions=3, difficulty="medium",
    )
    assert quiz.id is not None
    assert quiz.num_questions == 3
    assert quiz.difficulty == QuizDifficulty.medium
    assert len(quiz.questions) == 3

    async with session_factory() as s:
        m = await s.scalar(select(Material).where(Material.id == material_id))
        assert m.status == MaterialStatus.ready


@pytest.mark.asyncio
async def test_generate_quiz_retries_once_then_fails(session_factory, monkeypatch):
    material_id = await _seed_material(session_factory, with_chunks=True)

    from services.materials import generate as gen_mod

    calls = {"n": 0}

    class _FailProvider(AIProvider):
        async def generate_quiz(self, text, **kwargs):
            calls["n"] += 1
            raise AIProviderError("boom")

    monkeypatch.setattr(gen_mod, "get_ai_provider", lambda: _FailProvider())

    async def _no_sleep(_):
        return None
    monkeypatch.setattr(gen_mod.asyncio, "sleep", _no_sleep)

    with pytest.raises(AIProviderError):
        await gen_mod.generate_quiz_for_material(material_id=material_id, num_questions=3)
    assert calls["n"] == 2

    async with session_factory() as s:
        m = await s.scalar(select(Material).where(Material.id == material_id))
        assert m.status == MaterialStatus.failed
        assert m.error_message and "boom" in m.error_message


@pytest.mark.asyncio
async def test_generate_quiz_empty_material_fails(session_factory, monkeypatch):
    material_id = await _seed_material(session_factory, with_chunks=False)

    from services.materials import generate as gen_mod

    with pytest.raises(AIProviderError):
        await gen_mod.generate_quiz_for_material(material_id=material_id, num_questions=3)

    async with session_factory() as s:
        m = await s.scalar(select(Material).where(Material.id == material_id))
        assert m.status == MaterialStatus.failed
