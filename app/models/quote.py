from models.base import Base
from sqlalchemy import Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column


class MotivationalQuote(Base):
    __tablename__ = "motivational_quotes"

    text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    def __str__(self) -> str:
        return self.text[:60]
