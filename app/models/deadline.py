from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.faculty import Faculty
    from models.student_profile import StudentProfile


class Deadline(Base):
    """Admin tomonidan qo'yiladigan deadline (butun universitet yoki fakultet darajasida)."""
    __tablename__ = "deadlines"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    faculty_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("faculties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    faculty: Mapped["Faculty | None"] = relationship()

    def __str__(self) -> str:
        return self.title


class DeadlineSent(Base):
    """Qaysi eslatma qaysi talabaga yuborilganini kuzatuvchi jadval (dublikatdan himoya)."""
    __tablename__ = "deadline_sent"
    __table_args__ = (
        UniqueConstraint("deadline_id", "student_profile_id", "remind_type", name="uq_deadline_sent"),
    )

    deadline_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("deadlines.id", ondelete="CASCADE"), index=True
    )
    student_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True
    )
    remind_type: Mapped[str] = mapped_column(String(10))  # "24h" yoki "2h"


class PersonalDeadline(Base):
    """Talabaning o'zi qo'shadigan shaxsiy eslatma."""
    __tablename__ = "personal_deadlines"

    student_profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    deadline_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    reminded_24h: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    reminded_2h: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    student_profile: Mapped["StudentProfile"] = relationship()

    def __str__(self) -> str:
        return self.title
