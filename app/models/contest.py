from datetime import datetime
from typing import TYPE_CHECKING

from models.base import Base
from models.question import CorrectOption
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.telegram_user import TelegramUser


class Contest(Base):
    __tablename__ = "contests"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prize: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    end_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=3000)
    question_count: Mapped[int] = mapped_column(Integer, default=50)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    questions: Mapped[list["ContestQuestion"]] = relationship(
        "ContestQuestion",
        back_populates="contest",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ContestQuestion.order",
    )
    attempts: Mapped[list["ContestAttempt"]] = relationship(
        "ContestAttempt",
        back_populates="contest",
        cascade="all, delete-orphan",
    )

    def __str__(self) -> str:
        return self.title


class ContestQuestion(Base):
    __tablename__ = "contest_questions"

    contest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contests.id", ondelete="CASCADE")
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    option_a: Mapped[str] = mapped_column(String(512))
    option_b: Mapped[str] = mapped_column(String(512))
    option_c: Mapped[str] = mapped_column(String(512))
    option_d: Mapped[str] = mapped_column(String(512))
    correct_option: Mapped[CorrectOption] = mapped_column(
        Enum(CorrectOption, name="correct_option_enum", create_type=False),
        default=CorrectOption.A,
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    contest: Mapped["Contest"] = relationship("Contest", back_populates="questions")

    def __str__(self) -> str:
        return (self.text or "[rasm]")[:60]


class ContestAttempt(Base):
    __tablename__ = "contest_attempts"
    __table_args__ = (UniqueConstraint("user_id", "contest_id", name="uq_contest_attempt_user"),)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.id", ondelete="CASCADE")
    )
    contest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contests.id", ondelete="CASCADE")
    )
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0)
    answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    user: Mapped["TelegramUser"] = relationship("TelegramUser")
    contest: Mapped["Contest"] = relationship("Contest", back_populates="attempts")

    @property
    def percentage(self) -> int:
        if self.total == 0:
            return 0
        return round(self.score / self.total * 100)
