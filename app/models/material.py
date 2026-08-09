import enum
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.generated_quiz import GeneratedQuiz
    from models.material_chunk import MaterialChunk
    from models.student_profile import StudentProfile


class MaterialStatus(str, enum.Enum):
    uploaded = "uploaded"
    extracting = "extracting"
    generating = "generating"
    ready = "ready"
    failed = "failed"


class Material(Base):
    __tablename__ = "materials"

    student_profile_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_path: Mapped[str] = mapped_column(String(512))
    status: Mapped[MaterialStatus] = mapped_column(
        Enum(MaterialStatus, name="material_status_enum"),
        default=MaterialStatus.uploaded,
    )
    extracted_text_length: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    student_profile: Mapped["StudentProfile"] = relationship("StudentProfile")
    chunks: Mapped[list["MaterialChunk"]] = relationship(
        "MaterialChunk",
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="MaterialChunk.order",
    )
    generated_quizzes: Mapped[list["GeneratedQuiz"]] = relationship(
        "GeneratedQuiz",
        back_populates="material",
        cascade="all, delete-orphan",
    )

    def __str__(self) -> str:
        return self.title
