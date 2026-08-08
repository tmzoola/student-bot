from datetime import datetime
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.faculty import Faculty
    from models.telegram_user import TelegramUser


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    __table_args__ = (
        CheckConstraint("course_number BETWEEN 1 AND 4", name="ck_student_course_number"),
        CheckConstraint("semester IN (1, 2)", name="ck_student_semester"),
    )

    telegram_user_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_users.id", ondelete="CASCADE"), unique=True, index=True
    )
    student_id_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculties.id", ondelete="RESTRICT"), index=True
    )
    course_number: Mapped[int] = mapped_column(Integer)
    semester: Mapped[int] = mapped_column(Integer)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    approved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    telegram_user: Mapped["TelegramUser"] = relationship(back_populates="profile")
    faculty: Mapped["Faculty"] = relationship()

    def __str__(self) -> str:
        return f"{self.full_name} ({self.student_id_number})"
