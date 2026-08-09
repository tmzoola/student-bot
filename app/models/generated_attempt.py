from datetime import datetime
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import JSON, TIMESTAMP, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.generated_quiz import GeneratedQuiz
    from models.student_profile import StudentProfile


class GeneratedQuizAttempt(Base):
    __tablename__ = "generated_quiz_attempts"

    generated_quiz_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("generated_quizzes.id", ondelete="CASCADE"),
        index=True,
    )
    student_profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    generated_quiz: Mapped["GeneratedQuiz"] = relationship("GeneratedQuiz")
    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")

    @property
    def percentage(self) -> int:
        if self.total == 0:
            return 0
        return round(self.score / self.total * 100)
