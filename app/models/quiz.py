from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.question import Question
    from models.topic import Topic


class Quiz(Base):
    __tablename__ = "quizzes"

    topic_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=300)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    topic: Mapped["Topic"] = relationship("Topic", back_populates="quizzes")
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="quiz",
        lazy="selectin",
        order_by="Question.order",
    )

    def __str__(self) -> str:
        return self.title
