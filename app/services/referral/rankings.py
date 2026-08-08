"""Referral top-inviterlar reytingi servisi.

Bitta SQL bilan har bir foydalanuvchi uchun jami `join_count` (barcha
tracked_chatlar bo'yicha) va faol chatlar sonini yig'adi. Handler tanasi
yupqa qolishi uchun barcha aggregatsiya shu yerda.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from sqlalchemy import Integer, String, and_, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.referral import InviteLink, TrackedChat
from models.telegram_user import TelegramUser


@dataclass(slots=True)
class InviterRankRow:
    """Bitta foydalanuvchining reyting satri."""

    rank: int
    user_id: int
    telegram_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    total_invites: int
    active_chats: int

    @property
    def full_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) or (self.username or str(self.telegram_id))


async def get_top_inviters(
    session: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    tracked_chat_id: int | None = None,
    search: str | None = None,
) -> list[InviterRankRow]:
    """Eng ko'p taklif qilgan foydalanuvchilar reytingi.

    - Bitta SQL: `TelegramUser JOIN InviteLink` bo'yicha
      SUM(join_count), COUNT(DISTINCT tracked_chat_id).
    - `tracked_chat_id` berilsa, faqat shu chatning invite linki bo'yicha
      hisoblanadi (aslida bir user shu chatga bitta linki bor).
    - `search` — first_name / last_name / username / telegram_id bo'yicha ILIKE.
    - Faqat `revoked_at IS NULL` bo'lgan faol linklar hisobga olinadi.
    """

    total_invites = func.coalesce(func.sum(InviteLink.join_count), 0).label(
        "total_invites"
    )
    active_chats = func.count(func.distinct(InviteLink.tracked_chat_id)).label(
        "active_chats"
    )

    conditions = [InviteLink.revoked_at.is_(None)]
    if tracked_chat_id is not None:
        conditions.append(InviteLink.tracked_chat_id == tracked_chat_id)

    stmt = (
        select(
            TelegramUser.id.label("user_id"),
            TelegramUser.telegram_id,
            TelegramUser.first_name,
            TelegramUser.last_name,
            TelegramUser.username,
            total_invites,
            active_chats,
        )
        .join(InviteLink, InviteLink.user_id == TelegramUser.id)
        .where(and_(*conditions))
        .group_by(TelegramUser.id)
        .having(func.coalesce(func.sum(InviteLink.join_count), 0) > 0)
        .order_by(desc("total_invites"), TelegramUser.id.asc())
    )

    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                TelegramUser.first_name.ilike(needle),
                TelegramUser.last_name.ilike(needle),
                TelegramUser.username.ilike(needle),
                cast(TelegramUser.telegram_id, String).ilike(needle),
            )
        )

    stmt = stmt.limit(limit).offset(offset)

    result = await session.execute(stmt)
    raw_rows = result.all()

    rows: list[InviterRankRow] = []
    for i, r in enumerate(raw_rows, start=offset + 1):
        rows.append(
            InviterRankRow(
                rank=i,
                user_id=r.user_id,
                telegram_id=r.telegram_id,
                first_name=r.first_name,
                last_name=r.last_name,
                username=r.username,
                total_invites=int(r.total_invites or 0),
                active_chats=int(r.active_chats or 0),
            )
        )
    return rows


async def get_active_tracked_chats(
    session: AsyncSession,
) -> Sequence[TrackedChat]:
    """Filter dropdown uchun faol kuzatiladigan chatlar ro'yxati."""
    stmt = (
        select(TrackedChat)
        .where(TrackedChat.is_active.is_(True))
        .order_by(TrackedChat.title.asc())
    )
    return (await session.execute(stmt)).scalars().all()
