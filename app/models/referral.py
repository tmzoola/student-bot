"""Referral (taklif) tizimi modellari.

- TrackedChat  — bot admin qilib qo'shilgan kanal/guruh/supergruhlar
- InviteLink   — har bir (user, tracked_chat) uchun shaxsiy Telegram invite link
- InviteJoin   — kimning linki orqali kim va qachon qo'shilgani (audit + hisoblagich manbasi)
"""
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


class TrackedChat(Base):
    """Bot admin sifatida qo'shilgan Telegram chat (kanal/guruh/supergruh)."""

    __tablename__ = "tracked_chats"

    # Telegram chat_id manfiy uzun raqam bo'lishi mumkin — BigInteger majburiy.
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    # channel | group | supergroup
    type: Mapped[str] = mapped_column(String(32))
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Konkurs e'lonidagi "qo'shilish" tugmasi uchun havola. Public chatda
    # `username`dan `t.me/...` olinadi; private chat uchun admin shu yerga
    # doimiy invite link qo'yadi. NULL bo'lsa faqat `username`ga tayaniladi.
    invite_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    invite_links: Mapped[list["InviteLink"]] = relationship(
        "InviteLink",
        back_populates="tracked_chat",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __str__(self) -> str:
        return self.title or (self.username or str(self.chat_id))


class InviteLink(Base):
    """Foydalanuvchining ma'lum bir tracked_chat uchun shaxsiy invite linki."""

    __tablename__ = "invite_links"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "tracked_chat_id", name="uq_invite_links_user_chat"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        index=True,
    )
    tracked_chat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tracked_chats.id", ondelete="CASCADE"),
        index=True,
    )
    # Telegram tomonidan qaytarilgan `invite_link` (t.me/+HASH).
    invite_link: Mapped[str] = mapped_column(Text)
    # Telegram createChatInviteLink `name` parametri — biz `u{user.id}` shaklda beramiz.
    telegram_link_name: Mapped[str] = mapped_column(String(64))
    # Denormallashtirilgan hisoblagich (InviteJoin.is_counted=True bo'yicha sinxron).
    join_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    # Admin yoki servis tomonidan bekor qilingan sana (NULL = faol).
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    user: Mapped["TelegramUser"] = relationship("TelegramUser", lazy="select")
    tracked_chat: Mapped["TrackedChat"] = relationship(
        "TrackedChat", back_populates="invite_links", lazy="select"
    )
    joins: Mapped[list["InviteJoin"]] = relationship(
        "InviteJoin",
        back_populates="invite_link",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __str__(self) -> str:
        return f"InviteLink(user={self.user_id}, chat={self.tracked_chat_id})"


class InviteJoin(Base):
    """Ma'lum invite link orqali qo'shilgan foydalanuvchi hodisasi."""

    __tablename__ = "invite_joins"
    __table_args__ = (
        UniqueConstraint(
            "invite_link_id",
            "joined_user_tg_id",
            name="uq_invite_joins_link_user",
        ),
    )

    invite_link_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invite_links.id", ondelete="CASCADE"),
        index=True,
    )
    # Qo'shilgan foydalanuvchining Telegram ID'si (bizning users jadvalimizda
    # bo'lmasligi ham mumkin — shu sabab FK emas, BigInteger).
    joined_user_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    # Qo'shilgan foydalanuvchining Telegram username'i (`@` belgisisiz).
    # NULL bo'lishi mumkin — barcha foydalanuvchilar username o'rnatmaydi.
    joined_username: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    # Qo'shilgan foydalanuvchining ism-familiyasi (Telegram `full_name`).
    joined_full_name: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    # Foydalanuvchi chatni tark etgan sana (NULL = hozir ham a'zo).
    left_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    # `join_count` denormallashtirilgan hisoblagichga kiritilganmi.
    is_counted: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    # T-022 · Anti-fraud: grace period tugaydigan vaqt. NULL bo'lsa allaqachon
    # yakuniy holatda (counted yoki rad etilgan). Worker bu ustunni scan qiladi.
    pending_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )
    # T-022 · Anti-fraud rad etish sababi (masalan `new_account`,
    # `already_member`, `quick_leave`, `self_invite`). NULL bo'lsa rad etilmagan.
    reject_reason: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    invite_link: Mapped["InviteLink"] = relationship(
        "InviteLink", back_populates="joins", lazy="select"
    )

    def __str__(self) -> str:
        return f"InviteJoin(link={self.invite_link_id}, tg={self.joined_user_tg_id})"
