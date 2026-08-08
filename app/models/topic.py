from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.quiz import Quiz
    from models.subject import Subject


class Topic(Base):
    __tablename__ = "topics"

    subject_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subject: Mapped["Subject"] = relationship("Subject", back_populates="topics")
    quizzes: Mapped[list["Quiz"]] = relationship(
        "Quiz", back_populates="topic", lazy="selectin"
    )

    def __str__(self) -> str:
        return self.title
