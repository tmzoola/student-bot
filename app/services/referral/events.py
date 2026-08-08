"""Referral konkurs (event) servisi.

- `get_active_event`         — hozir faol bo'lgan eventni topadi.
- `get_or_create_participant` — foydalanuvchiga ketma-ket "Ishtirokchi №" beradi.
- `announcement_keyboard`     — e'lon uchun inline keyboard (join + Obuna bo'ldim).
- `join_buttons`             — faol tracked chatlardan qo'shilish tugmalari.

Handler tanasi yupqa qolishi uchun barcha DB va keyboard logikasi shu yerda.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.referral import TrackedChat
from models.referral_event import (
    EventReferral,
    ReferralEvent,
    ReferralEventParticipant,
)
from models.telegram_user import TelegramUser

logger = logging.getLogger(__name__)

# "✅ Obuna bo'ldim" tugmasi callback_data.
SUBSCRIBED_CB = "refevent:check"
# "🔄 Yangilash" tugmasi callback_data.
REFRESH_CB = "refevent:refresh"


async def get_active_event(
    session: AsyncSession, now: datetime
) -> ReferralEvent | None:
    """Hozir faol bo'lgan eventni qaytaradi (`is_active` va vaqt oralig'ida).

    Bir vaqtda bir nechta mos event bo'lsa, eng oxirgi boshlanadigani olinadi.
    """
    stmt = (
        select(ReferralEvent)
        .where(
            ReferralEvent.is_active.is_(True),
            ReferralEvent.starts_at <= now,
            ReferralEvent.ends_at >= now,
        )
        .order_by(ReferralEvent.starts_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_active_tracked_chats(session: AsyncSession) -> list[TrackedChat]:
    """Faol (`is_active=True`) kuzatiladigan chatlar ro'yxati."""
    result = await session.execute(
        select(TrackedChat)
        .where(TrackedChat.is_active.is_(True))
        .order_by(TrackedChat.id)
    )
    return list(result.scalars().all())


async def get_or_create_participant(
    session: AsyncSession, *, event_id: int, user_id: int
) -> ReferralEventParticipant:
    """`(event, user)` uchun ishtirokchini oladi yoki ketma-ket raqam bilan yaratadi.

    Raqam `MAX(number)+1` sifatida beriladi. Poyga holatida UNIQUE buzilsa
    (`event_id, number` yoki `event_id, user_id`), rollback qilib qayta o'qiladi.
    """
    existing = await _get_participant(session, event_id=event_id, user_id=user_id)
    if existing is not None:
        return existing

    for _ in range(5):
        next_number = (
            await session.execute(
                select(func.coalesce(func.max(ReferralEventParticipant.number), 0))
                .where(ReferralEventParticipant.event_id == event_id)
            )
        ).scalar_one() + 1

        participant = ReferralEventParticipant(
            event_id=event_id, user_id=user_id, number=next_number
        )
        session.add(participant)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            existing = await _get_participant(
                session, event_id=event_id, user_id=user_id
            )
            if existing is not None:
                return existing
            # `number` poygasi — qayta urinamiz.
            continue
        await session.refresh(participant)
        return participant

    # Juda kam ehtimolli — bu yergacha yetsa, oxirgi holatni qaytaramiz.
    existing = await _get_participant(session, event_id=event_id, user_id=user_id)
    if existing is None:
        raise RuntimeError("ishtirokchi raqamini berib bo'lmadi")
    return existing


async def _get_participant(
    session: AsyncSession, *, event_id: int, user_id: int
) -> ReferralEventParticipant | None:
    return (
        await session.execute(
            select(ReferralEventParticipant).where(
                ReferralEventParticipant.event_id == event_id,
                ReferralEventParticipant.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


# Bot ishga tushganda `get_me` orqali aniqlanadigan haqiqiy username. Shu tufayli
# deep-link doim ishlab turgan botga to'g'ri keladi (config qiymatiga bog'liq emas).
_BOT_USERNAME: str | None = None


def set_bot_username(username: str | None) -> None:
    """Bot startupida haqiqiy username'ni keshlaydi (`bot_main.py` chaqiradi)."""
    global _BOT_USERNAME
    if username:
        _BOT_USERNAME = username.lstrip("@")


def referral_deeplink(inviter_tg_id: int) -> str:
    """Taklif qiluvchining bot deep-link havolasi (`?start=ref_<id>`).

    Username: avval runtime'da aniqlangan (`get_me`), bo'lmasa `settings.BOT_USERNAME`.
    """
    username = _BOT_USERNAME or settings.BOT_USERNAME
    return f"https://t.me/{username}?start=ref_{inviter_tg_id}"


async def record_referral(
    session: AsyncSession,
    *,
    event_id: int,
    inviter_tg_id: int,
    invited_tg_id: int,
) -> None:
    """`/start ref_<inviter>` bosilganda kutilayotgan referralni yozadi.

    Idempotent: self-invite bloklanadi, bir eventda bir taklif qilingan
    foydalanuvchi faqat bir marta yoziladi (birinchi taklif qiluvchi g'olib).
    """
    if inviter_tg_id == invited_tg_id:
        return

    inviter = (
        await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == inviter_tg_id)
        )
    ).scalar_one_or_none()
    if inviter is None:
        return

    existing = (
        await session.execute(
            select(EventReferral.id).where(
                EventReferral.event_id == event_id,
                EventReferral.invited_tg_id == invited_tg_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return

    session.add(
        EventReferral(
            event_id=event_id,
            inviter_user_id=inviter.id,
            invited_tg_id=invited_tg_id,
            counted=False,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()  # poyga — boshqa so'rov yozib ulgurgan


async def count_referral_on_gate(
    session: AsyncSession,
    *,
    event_id: int,
    invited_tg_id: int,
    invited_user_id: int,
) -> None:
    """Taklif qilingan foydalanuvchi obuna gate'dan o'tganda referralni hisoblaydi."""
    row = (
        await session.execute(
            select(EventReferral).where(
                EventReferral.event_id == event_id,
                EventReferral.invited_tg_id == invited_tg_id,
                EventReferral.counted.is_(False),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return
    # O'z-o'ziga referral bo'lmasligi uchun qo'shimcha himoya.
    if row.inviter_user_id == invited_user_id:
        return
    row.counted = True
    row.invited_user_id = invited_user_id
    await session.commit()


@dataclass(slots=True)
class EventInviterRow:
    """Konkurs g'oliblar reytingi satri."""

    rank: int
    user_id: int
    telegram_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    tickets: int

    @property
    def full_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) or (self.username or str(self.telegram_id))


async def list_events(session: AsyncSession) -> list[ReferralEvent]:
    """Barcha konkurslar (eng yangisi birinchi) — reyting selektori uchun."""
    result = await session.execute(
        select(ReferralEvent).order_by(ReferralEvent.starts_at.desc())
    )
    return list(result.scalars().all())


async def get_event_leaderboard(
    session: AsyncSession,
    *,
    event_id: int,
    limit: int = 500,
    offset: int = 0,
    search: str | None = None,
) -> list[EventInviterRow]:
    """Konkursda eng ko'p chipta yiggan (hisoblangan referral) ishtirokchilar."""
    tickets = func.count(EventReferral.id).label("tickets")
    stmt = (
        select(
            TelegramUser.id.label("user_id"),
            TelegramUser.telegram_id,
            TelegramUser.first_name,
            TelegramUser.last_name,
            TelegramUser.username,
            tickets,
        )
        .join(EventReferral, EventReferral.inviter_user_id == TelegramUser.id)
        .where(
            EventReferral.event_id == event_id,
            EventReferral.counted.is_(True),
        )
        .group_by(TelegramUser.id)
        .order_by(tickets.desc(), TelegramUser.id.asc())
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

    rows = (await session.execute(stmt)).all()
    return [
        EventInviterRow(
            rank=i,
            user_id=r.user_id,
            telegram_id=r.telegram_id,
            first_name=r.first_name,
            last_name=r.last_name,
            username=r.username,
            tickets=int(r.tickets or 0),
        )
        for i, r in enumerate(rows, start=offset + 1)
    ]


async def referral_ticket_count(
    session: AsyncSession, *, event_id: int, inviter_user_id: int
) -> int:
    """Taklif qiluvchining shu eventdagi hisoblangan chiptalari soni."""
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(EventReferral)
                .where(
                    EventReferral.event_id == event_id,
                    EventReferral.inviter_user_id == inviter_user_id,
                    EventReferral.counted.is_(True),
                )
            )
        ).scalar_one()
    )


async def event_total_invited_count(
    session: AsyncSession, *, event_id: int
) -> int:
    """Konkurs bo'yicha jami taklif qilingan (hisoblangan) foydalanuvchilar soni."""
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(EventReferral)
                .where(
                    EventReferral.event_id == event_id,
                    EventReferral.counted.is_(True),
                )
            )
        ).scalar_one()
    )


def chat_join_url(chat: TrackedChat) -> str | None:
    """Chatga qo'shilish uchun ommaviy havola (`invite_url` yoki `t.me/username`)."""
    if chat.invite_url:
        return chat.invite_url
    if chat.username:
        return f"https://t.me/{chat.username.lstrip('@')}"
    return None


def _chat_label(chat: TrackedChat) -> str:
    icon = "📢" if chat.type == "channel" else "👥"
    return f"{icon} {chat.title}"


def join_buttons(chats: list[TrackedChat]) -> list[list[InlineKeyboardButton]]:
    """Faol chatlar uchun qo'shilish tugmalari (havolasi borlari)."""
    rows: list[list[InlineKeyboardButton]] = []
    for chat in chats:
        url = chat_join_url(chat)
        if url is None:
            continue
        rows.append([InlineKeyboardButton(text=_chat_label(chat), url=url)])
    return rows


def normalize_newlines(s: str | None) -> str:
    r"""Admin kiritgan literal `\n`, `\r\n`, `\t` ketma-ketliklarini haqiqiy
    belgilarga aylantiradi.

    Dashboard maydonida foydalanuvchi `\n` deb yozib qo'ysa (haqiqiy qator
    ko'chishi emas), Telegram'da qator ko'chishi ishlashi uchun uni real `\n`
    ga o'giramiz.
    """
    if not s:
        return ""
    return (
        s.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\\t", "\t")
    )


def _share_promo_text(announcement_text: str | None) -> str:
    """Ulashish uchun qisqa promo matn (share URL'ga sig'ishi uchun cheklangan).

    E'lon matnidagi ketma-ket bo'sh qatorlar (`\\n\\n...`) bitta qatorga
    qisqartiriladi — ulashilgan xabarda katta bo'sh joylar bo'lmasin.
    """
    base = (normalize_newlines(announcement_text) or "🎉 Konkursda ishtirok eting!").strip()
    # CRLF / CR ni LF ga keltiramiz, nbsp'ni oddiy probelga — aks holda `\r`
    # ketma-ket bo'sh qatorlarni "bo'lib" collapse'ga xalal beradi.
    base = base.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    base = re.sub(r"[ \t]+\n", "\n", base)      # qator oxiridagi probellar
    # 2+ bo'sh qator -> KO'PI BILAN 1 bo'sh qator (spacing saqlanadi).
    base = re.sub(r"\n{3,}", "\n\n", base)
    if len(base) > 800:
        base = base[:800].rstrip() + "…"
    return base + "\n\n🎁 Konkursda ishtirok eting va sovg'alarni yutib oling! 🏆"


def share_button(
    inviter_tg_id: int, share_text: str | None
) -> InlineKeyboardButton:
    """`t.me/share/url` tugmasi — inline mode TALAB QILMAYDI (har doim ishlaydi).

    Bosilganda native "ulashish" oynasi ochiladi va tanlangan chatga deep-link
    (`url`) + promo matn (`text`) yuboriladi. `url` bo'sh bo'lmasligi shart —
    aks holda ulashish oynasi hech narsa yubormaydi. Telegram `url`ni matndan
    oldin (tepada) ko'rsatadi — bu share/url'ning o'zgartirib bo'lmaydigan
    xususiyati.
    """
    deeplink = referral_deeplink(inviter_tg_id)
    text = _share_promo_text(share_text)
    url = (
        "https://t.me/share/url?url="
        + quote(deeplink, safe="")
        + "&text="
        + quote(text, safe="")
    )
    return InlineKeyboardButton(text="📤 Do'stlarga ulashish", url=url)


def announcement_keyboard(
    inviter_tg_id: int, announcement_text: str | None
) -> InlineKeyboardMarkup:
    """E'lon uchun inline keyboard: faqat "Qatnashaman".

    "Do'stlarga ulashish" bu yerda KO'RSATILMAYDI — foydalanuvchi avval
    "Qatnashaman" bosib a'zolikdan o'tishi kerak. Aks holda a'zo bo'lmagan
    ishtirokchi havolani ulashsa, taklif chiptalari sanalmaydi. Ulashish tugmasi
    a'zolik tasdiqlangach keyingi qadamdagi chipta xabarida chiqadi
    (`_ticket_keyboard`). Chat qo'shilish tugmalari ham bu yerda ko'rsatilmaydi —
    "Qatnashaman" bosgach yetishmayotgan chatlar keyingi xabarda chiqadi.

    `inviter_tg_id`/`announcement_text` endi ishlatilmaydi, ammo chaqiruvchi
    imzosini buzmaslik uchun saqlanadi.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Qatnashaman", callback_data=SUBSCRIBED_CB)],
        ]
    )
