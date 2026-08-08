"""Guruh guard boti (@tozakanal_bot) uchun modellar.

- JoinEvent   — guruhga qo'shilgan HAR BIR a'zo (toza ham, shubhali ham)
- FlaggedUser — faqat 18+ shubhasi bilan flag qilinganlar (alohida jadval)
"""
from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class JoinEvent(Base):
    __tablename__ = "guard_join_events"

    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(256))
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_title: Mapped[str | None] = mapped_column(String(256))
    has_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    nsfw_score: Mapped[float] = mapped_column(Float, default=0.0)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class FlaggedUser(Base):
    __tablename__ = "guard_flagged_users"

    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(256))
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    chat_title: Mapped[str | None] = mapped_column(String(256))
    nsfw_score: Mapped[float] = mapped_column(Float, default=0.0)
    reasons: Mapped[str] = mapped_column(Text, default="")
    # Flag'ga sabab bo'lgan profil rasmi (/media/... URL yo'li)
    photo_path: Mapped[str | None] = mapped_column(String(512))
    # pending | banned | ignored
    action: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    decided_by: Mapped[str | None] = mapped_column(String(256))
    decided_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
