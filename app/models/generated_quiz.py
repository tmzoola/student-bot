import enum
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.generated_question import GeneratedQuestion
    from models.material import Material
    from models.student_profile import StudentProfile


class QuizDifficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class GeneratedQuiz(Base):
    __tablename__ = "generated_quizzes"

    material_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("materials.id", ondelete="CASCADE"),
        index=True,
    )
    student_profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[QuizDifficulty] = mapped_column(
        Enum(QuizDifficulty, name="quiz_difficulty_enum"),
        default=QuizDifficulty.medium,
    )
    language: Mapped[str] = mapped_column(String(8), default="uz")
    num_questions: Mapped[int] = mapped_column(Integer, default=0)

    material: Mapped["Material"] = relationship("Material", back_populates="generated_quizzes")
    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")
    questions: Mapped[list["GeneratedQuestion"]] = relationship(
        "GeneratedQuestion",
        back_populates="generated_quiz",
        cascade="all, delete-orphan",
        order_by="GeneratedQuestion.order",
        lazy="selectin",
    )

    def __str__(self) -> str:
        return self.title
