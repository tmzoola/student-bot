from datetime import datetime
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.student_profile import StudentProfile


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    last_active_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )

    profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="telegram_user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def is_registered(self) -> bool:
        return bool(self.phone and (self.first_name or self.last_name))

    @property
    def full_name(self) -> str:
        parts = filter(None, [self.first_name, self.last_name])
        return " ".join(parts) or self.username or str(self.telegram_id)

    def __str__(self) -> str:
        return self.full_name
