from datetime import datetime

from models.base import Base
from sqlalchemy import ForeignKey, Integer, JSON, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.id", ondelete="CASCADE")
    )
    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE")
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)
    # {str(question_id): "A"/"B"/"C"/"D"}
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    user: Mapped["TelegramUser"] = relationship("TelegramUser")
    quiz: Mapped["Quiz"] = relationship("Quiz")

    @property
    def percentage(self) -> int:
        if self.total == 0:
            return 0
        return round(self.score / self.total * 100)

    @property
    def points(self) -> int:
        # 2 points per correct answer (business rule)
        return self.score * 2
