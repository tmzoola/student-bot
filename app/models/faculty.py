from models.base import Base
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Faculty(Base):
    __tablename__ = "faculties"

    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    subjects: Mapped[list["Subject"]] = relationship(  # noqa: F821
        back_populates="faculty",
        cascade="all, delete-orphan",
    )

    def __str__(self) -> str:
        return self.name
