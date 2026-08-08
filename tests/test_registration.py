"""T-201 uchun DB-level smoke: StudentProfile yaratilishi va constraint'lar."""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.faculty import Faculty
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser


@pytest.mark.asyncio
async def test_create_student_profile(db):
    faculty = Faculty(name="Kompyuter injiniringi", code="CE", is_active=True)
    user = TelegramUser(telegram_id=111, username="u1", first_name="A")
    db.add_all([faculty, user])
    await db.commit()
    await db.refresh(faculty)
    await db.refresh(user)

    profile = StudentProfile(
        telegram_user_id=user.id,
        student_id_number="2024-CE-0001",
        full_name="Test Talaba",
        faculty_id=faculty.id,
        course_number=2,
        semester=1,
        is_approved=False,
    )
    db.add(profile)
    await db.commit()

    loaded = await db.scalar(select(StudentProfile).where(StudentProfile.telegram_user_id == user.id))
    assert loaded is not None
    assert loaded.student_id_number == "2024-CE-0001"
    assert loaded.is_approved is False


@pytest.mark.asyncio
async def test_duplicate_student_id_rejected(db):
    faculty = Faculty(name="F", code="F1")
    u1 = TelegramUser(telegram_id=201, first_name="A")
    u2 = TelegramUser(telegram_id=202, first_name="B")
    db.add_all([faculty, u1, u2])
    await db.commit()
    await db.refresh(faculty); await db.refresh(u1); await db.refresh(u2)

    db.add(StudentProfile(
        telegram_user_id=u1.id, student_id_number="DUP-1",
        full_name="A", faculty_id=faculty.id, course_number=1, semester=1,
    ))
    await db.commit()

    db.add(StudentProfile(
        telegram_user_id=u2.id, student_id_number="DUP-1",
        full_name="B", faculty_id=faculty.id, course_number=1, semester=1,
    ))
    with pytest.raises(IntegrityError):
        await db.commit()
