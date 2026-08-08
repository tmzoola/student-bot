from datetime import datetime

from models.base import Base
from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Bot could not deliver messages (user blocked the bot) — auto-managed.
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Admin blacklist — user is forbidden from using the bot and WebApp.
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    # Last time the user actively used the bot or WebApp.
    last_active_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
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
