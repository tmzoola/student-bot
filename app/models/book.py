from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.topic import Topic


class Book(Base):
    __tablename__ = "books"

    topic_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form type: Darslik / Qo'llanma / Qonun hujjati / Metodik ...
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512))  # relative to media root
    file_name: Mapped[str] = mapped_column(String(255))  # original filename
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # bytes
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    topic: Mapped["Topic | None"] = relationship("Topic")

    def __str__(self) -> str:
        return self.title
