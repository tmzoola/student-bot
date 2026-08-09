from typing import TYPE_CHECKING

from models.base import Base
from models.question import CorrectOption
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.generated_quiz import GeneratedQuiz


class GeneratedQuestion(Base):
    __tablename__ = "generated_questions"

    generated_quiz_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("generated_quizzes.id", ondelete="CASCADE"),
        index=True,
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    option_a: Mapped[str] = mapped_column(String(1024))
    option_b: Mapped[str] = mapped_column(String(1024))
    option_c: Mapped[str] = mapped_column(String(1024))
    option_d: Mapped[str] = mapped_column(String(1024))
    correct_option: Mapped[CorrectOption] = mapped_column(
        Enum(CorrectOption, name="correct_option_enum", create_type=False),
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    generated_quiz: Mapped["GeneratedQuiz"] = relationship(
        "GeneratedQuiz", back_populates="questions"
    )

    def __str__(self) -> str:
        return self.text[:60]
