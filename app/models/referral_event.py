"""Referral konkurs (event) modellari.

- ReferralEvent            — vaqt bilan chegaralangan konkurs e'loni.
- ReferralEventParticipant — eventga qo'shilgan foydalanuvchi ("Ishtirokchi №").

`/start` bosilganda faol event (`is_active` va `starts_at <= now <= ends_at`)
bo'lsa, foydalanuvchiga e'lon (rasm + matn + "Obuna bo'ldim") ko'rsatiladi.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.telegram_user import TelegramUser


class ReferralEvent(Base):
    """Admin sozlaydigan referral konkurs e'loni."""

    __tablename__ = "referral_events"

    title: Mapped[str] = mapped_column(String(255))
    # E'lon matni (Telegram caption / message body — /start'da ko'rsatiladi).
    announcement_text: Mapped[str] = mapped_column(Text)
    # "Do'stlarga ulashish"da yuboriladigan matn. Bo'sh bo'lsa `announcement_text`
    # ishlatiladi.
    share_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # E'lon rasmi — URL yoki Telegram file_id (RewardTier.image_url uslubida).
    # NULL bo'lsa e'lon faqat matn sifatida yuboriladi.
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Muvaffaqiyatli "Obuna bo'ldim"dan keyingi chipta xabari sarlavhasi
    # (ixtiyoriy). NULL bo'lsa standart matn ishlatiladi.
    success_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )

    participants: Mapped[list["ReferralEventParticipant"]] = relationship(
        "ReferralEventParticipant",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __str__(self) -> str:
        return self.title or f"ReferralEvent({self.id})"


class EventReferral(Base):
    """Bot deep-link (`?start=ref_<id>`) orqali taklif qilingan foydalanuvchi.

    `/start ref_<inviter>` bosilganda `counted=False` bilan yoziladi; taklif
    qilingan foydalanuvchi obuna gate'dan (Obuna bo'ldim) o'tgach `counted=True`
    bo'ladi va bu taklif qiluvchiga chipta sifatida hisoblanadi. Har bir taklif
    qilingan foydalanuvchi bitta eventda faqat bir marta hisoblanadi.
    """

    __tablename__ = "event_referrals"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "invited_tg_id", name="uq_event_referrals_event_invited"
        ),
    )

    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("referral_events.id", ondelete="CASCADE"),
        index=True,
    )
    # Taklif qiluvchi (bizning users jadvalimizdagi PK).
    inviter_user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        index=True,
    )
    # Taklif qilingan foydalanuvchining Telegram ID'si.
    invited_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # Taklif qilingan foydalanuvchi ro'yxatdan o'tgach — uning PK'si (NULL ham bo'ladi).
    invited_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Obuna gate'dan o'tib, chipta sifatida hisoblanganmi.
    counted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    event: Mapped["ReferralEvent"] = relationship(
        "ReferralEvent", lazy="select"
    )
    inviter: Mapped["TelegramUser"] = relationship(
        "TelegramUser", foreign_keys=[inviter_user_id], lazy="select"
    )
    invited: Mapped["TelegramUser | None"] = relationship(
        "TelegramUser", foreign_keys=[invited_user_id], lazy="select"
    )

    def __str__(self) -> str:
        return f"EventReferral(event={self.event_id}, invited={self.invited_tg_id})"


class ReferralEventParticipant(Base):
    """Eventga qo'shilgan foydalanuvchi va uning ketma-ket "Ishtirokchi №"'si."""

    __tablename__ = "referral_event_participants"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "user_id", name="uq_event_participants_event_user"
        ),
        UniqueConstraint(
            "event_id", "number", name="uq_event_participants_event_number"
        ),
    )

    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("referral_events.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        index=True,
    )
    # Event bo'yicha ketma-ket ishtirokchi raqami ("Ishtirokchi №3701").
    number: Mapped[int] = mapped_column(Integer)

    event: Mapped["ReferralEvent"] = relationship(
        "ReferralEvent", back_populates="participants", lazy="select"
    )
    user: Mapped["TelegramUser"] = relationship("TelegramUser", lazy="select")

    def __str__(self) -> str:
        return f"Participant(event={self.event_id}, number={self.number})"
