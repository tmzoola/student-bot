"""T-301 · UserStats hisoblash — sun'iy attempt data."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from models.attempt import QuizAttempt
from models.faculty import Faculty
from models.generated_attempt import GeneratedQuizAttempt
from models.generated_question import GeneratedQuestion
from models.generated_quiz import GeneratedQuiz, QuizDifficulty
from models.material import Material, MaterialStatus
from models.question import CorrectOption, Question
from models.quiz import Quiz
from models.student_profile import StudentProfile
from models.subject import Subject
from models.telegram_user import TelegramUser
from models.topic import Topic
from services.insights.stats import compute_user_stats


async def _seed(session_factory) -> int:
    """Ikkita Topic (matem, fiz) + 1 AI material. Attempts data:

    Matem (kuchli): 3 urinish, o'rtacha ~85%
    Fizika (zaif):  3 urinish, o'rtacha ~30%
    AI material:    2 urinish, o'rtacha 50%
    """
    async with session_factory() as s:
        fac = Faculty(name="Kompyuter", code="KI")
        user = TelegramUser(telegram_id=1, first_name="U")
        s.add_all([fac, user])
        await s.commit()

        subj = Subject(
            faculty_id=fac.id, name="Matematika", code="MAT1",
            course_number=1, semester=1,
        )
        subj2 = Subject(
            faculty_id=fac.id, name="Fizika", code="FIZ1",
            course_number=1, semester=1,
        )
        prof = StudentProfile(
            telegram_user_id=user.id,
            student_id_number="S-1", full_name="Ali",
            faculty_id=fac.id, course_number=1, semester=1,
            is_approved=True,
        )
        s.add_all([subj, subj2, prof])
        await s.commit()

        t_mat = Topic(subject_id=subj.id, title="Chiziqli tenglama")
        t_fiz = Topic(subject_id=subj2.id, title="Mexanika")
        s.add_all([t_mat, t_fiz])
        await s.commit()

        q_mat = Quiz(topic_id=t_mat.id, title="MAT test")
        q_fiz = Quiz(topic_id=t_fiz.id, title="FIZ test")
        s.add_all([q_mat, q_fiz])
        await s.commit()

        now = datetime.now(timezone.utc)

        # Matem: 3 urinish, 9/10, 8/10, 9/10 -> ~87%
        for score in (9, 8, 9):
            s.add(QuizAttempt(
                student_profile_id=prof.id, quiz_id=q_mat.id,
                score=score, total=10, completed_at=now - timedelta(days=1),
            ))
        # Fizika: 3 urinish, 3/10, 3/10, 4/10 -> ~33%
        for score in (3, 3, 4):
            s.add(QuizAttempt(
                student_profile_id=prof.id, quiz_id=q_fiz.id,
                score=score, total=10, completed_at=now - timedelta(days=2),
            ))

        # AI material
        mat = Material(
            student_profile_id=prof.id, title="Konspekt-1",
            filename="k.pdf", mime="application/pdf", size_bytes=1,
            storage_path="/tmp/k.pdf", status=MaterialStatus.ready,
        )
        s.add(mat)
        await s.commit()
        gq = GeneratedQuiz(
            material_id=mat.id, student_profile_id=prof.id,
            title="AI test", difficulty=QuizDifficulty.medium,
            language="uz", num_questions=10,
        )
        s.add(gq)
        await s.commit()
        for score in (5, 5):
            s.add(GeneratedQuizAttempt(
                generated_quiz_id=gq.id, student_profile_id=prof.id,
                score=score, total=10, completed_at=now - timedelta(days=3),
            ))
        await s.commit()

        return prof.id


@pytest.mark.asyncio
async def test_compute_user_stats_overall_and_topics(session_factory):
    profile_id = await _seed(session_factory)
    async with session_factory() as s:
        stats = await compute_user_stats(s, profile_id)

    assert stats.attempts_total == 8  # 3+3+2
    # (9+8+9 + 3+3+4 + 5+5) / (10*8) = 46/80 = 57.5% -> 58
    assert stats.overall_accuracy_pct == 58

    titles = {t.topic_title for t in stats.by_topic}
    assert "Chiziqli tenglama" in titles
    assert "Mexanika" in titles
    assert "Konspekt-1" in titles  # AI material topic sifatida

    # Kuchli = matematika, Zaif = fizika
    assert stats.top_strengths[0].topic_title == "Chiziqli tenglama"
    assert stats.top_weaknesses[0].topic_title == "Mexanika"
    assert stats.top_weaknesses[0].accuracy_pct < 50


@pytest.mark.asyncio
async def test_compute_user_stats_ignores_single_attempt_topics(session_factory):
    """Faqat 1 urinish qilingan mavzu by_topic ga tushmaydi (min 2)."""
    async with session_factory() as s:
        fac = Faculty(name="F", code="F1")
        user = TelegramUser(telegram_id=2, first_name="U")
        s.add_all([fac, user])
        await s.commit()
        subj = Subject(faculty_id=fac.id, name="S", code="S1", course_number=1, semester=1)
        prof = StudentProfile(
            telegram_user_id=user.id, student_id_number="S-2",
            full_name="B", faculty_id=fac.id,
            course_number=1, semester=1, is_approved=True,
        )
        s.add_all([subj, prof])
        await s.commit()
        top = Topic(subject_id=subj.id, title="X")
        s.add(top)
        await s.commit()
        q = Quiz(topic_id=top.id, title="q")
        s.add(q)
        await s.commit()
        s.add(QuizAttempt(
            student_profile_id=prof.id, quiz_id=q.id,
            score=5, total=10, completed_at=datetime.now(timezone.utc),
        ))
        await s.commit()
        stats = await compute_user_stats(s, prof.id)
    assert stats.attempts_total == 1
    assert stats.by_topic == []  # 1 urinish — chiqmaydi
    assert stats.by_subject != []  # subject bo'yicha 1+ ham chiqadi
    assert stats.top_weaknesses == []


@pytest.mark.asyncio
async def test_compute_user_stats_empty(session_factory):
    async with session_factory() as s:
        fac = Faculty(name="F", code="FZ")
        user = TelegramUser(telegram_id=3, first_name="U")
        s.add_all([fac, user])
        await s.commit()
        prof = StudentProfile(
            telegram_user_id=user.id, student_id_number="S-3",
            full_name="C", faculty_id=fac.id,
            course_number=1, semester=1, is_approved=True,
        )
        s.add(prof)
        await s.commit()
        stats = await compute_user_stats(s, prof.id)
    assert stats.attempts_total == 0
    assert stats.overall_accuracy_pct == 0
    assert stats.by_topic == []
    assert len(stats.recent_trend) == 4  # 4 hafta, hammasi 0
    for tp in stats.recent_trend:
        assert tp.attempts == 0
        assert tp.accuracy_pct == 0


# Faylni ishlatilmayotgan importlarni "used" qilamiz (SQLAlchemy mapping).
_ = (GeneratedQuestion, Question, CorrectOption)
