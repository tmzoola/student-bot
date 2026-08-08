from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.topic import Topic
    from models.module import Module
    from models.question import Question


class Quiz(Base):
    __tablename__ = "quizzes"

    topic_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    module_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, default=300)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    topic: Mapped["Topic | None"] = relationship("Topic", back_populates="quizzes")
    module: Mapped["Module | None"] = relationship("Module")
    questions: Mapped[list["Question"]] = relationship(
        "Question",
        back_populates="quiz",
        lazy="selectin",
        order_by="Question.order",
    )

    def __str__(self) -> str:
        return self.title
