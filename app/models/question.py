import enum
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.quiz import Quiz


class CorrectOption(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Question(Base):
    __tablename__ = "questions"

    quiz_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quizzes.id", ondelete="CASCADE")
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    option_a: Mapped[str] = mapped_column(String(512))
    option_b: Mapped[str] = mapped_column(String(512))
    option_c: Mapped[str] = mapped_column(String(512))
    option_d: Mapped[str] = mapped_column(String(512))
    correct_option: Mapped[CorrectOption] = mapped_column(
        Enum(CorrectOption, name="correct_option_enum"), default=CorrectOption.A
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    quiz: Mapped["Quiz"] = relationship("Quiz", back_populates="questions")

    def __str__(self) -> str:
        return (self.text or "[rasm]")[:60]
