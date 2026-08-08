from models.base import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        CheckConstraint("course_number BETWEEN 1 AND 4", name="ck_subject_course_number"),
        CheckConstraint("semester IN (1, 2)", name="ck_subject_semester"),
        UniqueConstraint("faculty_id", "code", name="uq_subject_faculty_code"),
    )

    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculties.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(32))
    course_number: Mapped[int] = mapped_column(Integer)
    semester: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    faculty: Mapped["Faculty"] = relationship(back_populates="subjects")  # noqa: F821
    topics: Mapped[list["Topic"]] = relationship(  # noqa: F821
        "Topic",
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="Topic.order",
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.course_number}-kurs, {self.semester}-semestr)"
