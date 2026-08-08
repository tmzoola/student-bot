"""T-021 · Referral sovg'a (reward) tizimi modellari.

- RewardTier — admin sozlaydigan mukofot bosqichi (masalan: "Bronza — 10 do'st").
- UserReward — foydalanuvchi qaysi tier'ni qozongan/olgan (audit va idempotentlik).

Har bir user + tier juftligi uchun bitta UserReward yozuvi bo'ladi
(UNIQUE(user_id, reward_tier_id)), shu tufayli `evaluate_user_rewards`
qayta chaqirilsa ham dublikat yaratmaydi.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
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


class RewardTier(Base):
    """Admin tomonidan sozlanadigan sovg'a bosqichi.

    `required_invites` — foydalanuvchining jami `join_count` shu qiymatga
    yetganda tier "qozonilgan" hisoblanadi. UNIQUE — bir threshold uchun
    faqat bitta tier bo'lishi mumkin (aks holda evaluate ikki tomonlama
    ambiguous).
    """

    __tablename__ = "reward_tiers"
    __table_args__ = (
        UniqueConstraint(
            "required_invites", name="uq_reward_tiers_required_invites"
        ),
    )

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_invites: Mapped[int] = mapped_column(Integer, index=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_rewards: Mapped[list["UserReward"]] = relationship(
        "UserReward",
        back_populates="reward_tier",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __str__(self) -> str:
        return self.title or f"RewardTier({self.required_invites})"


class UserReward(Base):
    """Foydalanuvchi qozongan reward tier'ining audit yozuvi.

    - `earned_at` — foydalanuvchi thresholdga yetgan payt (avtomatik).
    - `claimed_at` — admin sovg'ani berildi deb belgilagan payt (NULL = kutmoqda).
    - `note` — admin izohi (masalan yetkazish tafsiloti).
    """

    __tablename__ = "user_rewards"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "reward_tier_id", name="uq_user_rewards_user_tier"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_users.id", ondelete="CASCADE"),
        index=True,
    )
    reward_tier_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reward_tiers.id", ondelete="CASCADE"),
        index=True,
    )
    earned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["TelegramUser"] = relationship("TelegramUser", lazy="select")
    reward_tier: Mapped["RewardTier"] = relationship(
        "RewardTier", back_populates="user_rewards", lazy="select"
    )

    def __str__(self) -> str:
        return f"UserReward(user={self.user_id}, tier={self.reward_tier_id})"
