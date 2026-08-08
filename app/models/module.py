from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.topic import Topic


class Module(Base):
    __tablename__ = "modules"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)  # FA class or emoji
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)  # hex color
    order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="module", lazy="selectin", order_by="Topic.order"
    )

    def __str__(self) -> str:
        return self.title
