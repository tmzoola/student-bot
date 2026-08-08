"""T-018 · Invite link orqali qo'shilish / chiqishlarni yozib borish servisi.

`chat_member` update handler tanasi yupqa bo'lishi uchun barcha DB logikasi shu
yerda joylashgan. `InviteJoin` yozuvi `UNIQUE(invite_link_id, joined_user_tg_id)`
orqali dublikatlardan himoyalangan, `InviteLink.join_count` esa atomik
`UPDATE ... SET join_count = join_count + 1` bilan yangilanadi.

T-022 · Anti-fraud MVP:
  - self-invite ban (avvaldan bor)
  - min account age (`MIN_TG_USER_ID_FOR_INVITE`) — reject_reason='new_account'
  - already_member — foydalanuvchi shu chatda boshqa faol join yozuviga ega
    bo'lsa, reject_reason='already_member'
  - grace period (`MIN_STAY_MINUTES`) — join darhol hisoblanmaydi, `pending_until`
    ga vaqt yoziladi; worker (`pending_joins_worker.py`) o'sha muddat o'tgach
    `is_counted=True` qiladi va `evaluate_user_rewards` chaqiradi.
  - quick leave — grace period ichida chiqib ketsa, `is_counted=False` qoladi,
    `reject_reason='quick_leave'` yoziladi.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.base import TASHKENT_TZ
from models.referral import InviteJoin, InviteLink, TrackedChat
from models.rewards import RewardTier
from models.telegram_user import TelegramUser
from services.referral.rewards import evaluate_user_rewards

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class JoinResult:
    """`record_join` natijasi.

    - `counted` — join darhol hisoblanganmi (grace period o'tmaguncha False).
      Grace period tugagach worker `is_counted=True` qiladi.
    - `inviter_tg_id` — invite link egasining Telegram ID'si (worker tabriknoma
      yuborishi uchun; `record_join` darhol biror narsa yubormaydi).
    - `newly_earned_rewards` — shu chaqiruvda yangi qozonilgan reward tier'lari.
      Grace bilan endi bu doim bo'sh; worker `pending_until` tugagach hisoblaydi.
    - `pending` — yozuv grace period'da kutmoqdami.
    - `reject_reason` — rad etilgan bo'lsa, sabab kaliti (masalan `new_account`).
    """

    counted: bool
    inviter_tg_id: int | None = None
    newly_earned_rewards: list[RewardTier] = field(default_factory=list)
    pending: bool = False
    reject_reason: str | None = None

    def __bool__(self) -> bool:  # eski `if await record_join(...)` chaqiruvlar uchun.
        return self.counted or self.pending


async def _user_already_in_chat(
    session: AsyncSession,
    *,
    tracked_chat_id: int,
    joined_user_tg_id: int,
    exclude_invite_link_id: int | None = None,
) -> bool:
    """Foydalanuvchi shu tracked_chat'da boshqa faol InviteJoin'ga egami."""
    stmt = (
        select(InviteJoin.id)
        .join(InviteLink, InviteJoin.invite_link_id == InviteLink.id)
        .where(
            InviteLink.tracked_chat_id == tracked_chat_id,
            InviteJoin.joined_user_tg_id == joined_user_tg_id,
            InviteJoin.left_at.is_(None),
        )
        .limit(1)
    )
    if exclude_invite_link_id is not None:
        stmt = stmt.where(InviteJoin.invite_link_id != exclude_invite_link_id)
    row = (await session.execute(stmt)).first()
    return row is not None


async def record_join(
    session: AsyncSession,
    *,
    tracked_chat_tg_id: int,
    joined_user_tg_id: int,
    invite_link_str: str,
    joined_username: str | None = None,
    joined_full_name: str | None = None,
) -> JoinResult:
    """Foydalanuvchining ma'lum invite link orqali qo'shilishini yozadi.

    T-022'dan boshlab yozuv darhol counted qilinmaydi — `pending_until` ga
    `MIN_STAY_MINUTES` keyingi vaqt qo'yiladi va background worker
    (`pending_joins_worker`) grace period tugagach counted'ga o'tkazadi va
    `evaluate_user_rewards` chaqiradi.
    """
    # 1) TrackedChat + InviteLink birgalikda topamiz.
    stmt = (
        select(InviteLink, TrackedChat)
        .join(TrackedChat, InviteLink.tracked_chat_id == TrackedChat.id)
        .where(
            TrackedChat.chat_id == tracked_chat_tg_id,
            InviteLink.invite_link == invite_link_str,
        )
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        logger.debug(
            "record_join: mos InviteLink topilmadi (chat_tg=%s link=%s)",
            tracked_chat_tg_id,
            invite_link_str,
        )
        return JoinResult(counted=False)
    invite_link: InviteLink = row[0]
    tracked_chat: TrackedChat = row[1]

    # 2) O'z-o'zini invite qilishni bloklash.
    owner = await session.get(TelegramUser, invite_link.user_id)
    if owner is not None and owner.telegram_id == joined_user_tg_id:
        logger.info(
            "record_join: o'z-o'ziga invite bloklandi (user_id=%s tg=%s)",
            invite_link.user_id,
            joined_user_tg_id,
        )
        return JoinResult(counted=False, reject_reason="self_invite")

    # 3) T-022 · Min account age (Telegram ID heuristikasi).
    min_tg_cutoff = settings.MIN_TG_USER_ID_FOR_INVITE
    if min_tg_cutoff is not None and joined_user_tg_id > min_tg_cutoff:
        logger.info(
            "record_join: yangi akkaunt rad etildi "
            "(tg=%s cutoff=%s)",
            joined_user_tg_id,
            min_tg_cutoff,
        )
        await _upsert_rejected(
            session,
            invite_link_id=invite_link.id,
            joined_user_tg_id=joined_user_tg_id,
            reason="new_account",
            joined_username=joined_username,
            joined_full_name=joined_full_name,
        )
        await session.commit()
        return JoinResult(counted=False, reject_reason="new_account")

    # 4) T-022 · Foydalanuvchi shu chatda boshqa link orqali allaqachon a'zomi?
    if await _user_already_in_chat(
        session,
        tracked_chat_id=tracked_chat.id,
        joined_user_tg_id=joined_user_tg_id,
        exclude_invite_link_id=invite_link.id,
    ):
        logger.info(
            "record_join: allaqachon shu chatda a'zo (chat=%s tg=%s)",
            tracked_chat.id,
            joined_user_tg_id,
        )
        await _upsert_rejected(
            session,
            invite_link_id=invite_link.id,
            joined_user_tg_id=joined_user_tg_id,
            reason="already_member",
            joined_username=joined_username,
            joined_full_name=joined_full_name,
        )
        await session.commit()
        return JoinResult(counted=False, reject_reason="already_member")

    # 5) Mavjud InviteJoin yozuvini tekshiramiz (qaytib qo'shilish holati).
    existing_stmt = select(InviteJoin).where(
        InviteJoin.invite_link_id == invite_link.id,
        InviteJoin.joined_user_tg_id == joined_user_tg_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()

    now = datetime.now(TASHKENT_TZ)
    pending_until = now + timedelta(minutes=settings.MIN_STAY_MINUTES)

    if existing is not None:
        # Yangi identity ma'lumotlari mavjud bo'lsa, har doim yangilaymiz —
        # foydalanuvchi username yoki ismini o'zgartirgan bo'lishi mumkin.
        if joined_username is not None:
            existing.joined_username = joined_username
        if joined_full_name is not None:
            existing.joined_full_name = joined_full_name
        if existing.is_counted and existing.left_at is None:
            # Allaqachon a'zo va hisoblangan — hech nima qilmaymiz.
            logger.debug(
                "record_join: dublikat, allaqachon counted "
                "(invite_link_id=%s tg=%s)",
                invite_link.id,
                joined_user_tg_id,
            )
            if joined_username is not None or joined_full_name is not None:
                await session.commit()
            return JoinResult(counted=False)
        if existing.pending_until is not None and existing.left_at is None:
            # Grace period davom etmoqda — takroriy update kerak emas.
            logger.debug(
                "record_join: dublikat, pending "
                "(invite_link_id=%s tg=%s)",
                invite_link.id,
                joined_user_tg_id,
            )
            if joined_username is not None or joined_full_name is not None:
                await session.commit()
            return JoinResult(counted=False, pending=True)
        # Qaytib qo'shildi — grace period qayta boshlanadi.
        existing.left_at = None
        existing.is_counted = False
        existing.pending_until = pending_until
        existing.reject_reason = None
        await session.commit()
        logger.info(
            "record_join: qayta qo'shildi (pending) "
            "(invite_link_id=%s tg=%s pending_until=%s)",
            invite_link.id,
            joined_user_tg_id,
            pending_until.isoformat(),
        )
        return JoinResult(
            counted=False,
            pending=True,
            inviter_tg_id=owner.telegram_id if owner is not None else None,
        )

    # 6) Yangi InviteJoin — grace period bilan pending.
    session.add(
        InviteJoin(
            invite_link_id=invite_link.id,
            joined_user_tg_id=joined_user_tg_id,
            joined_username=joined_username,
            joined_full_name=joined_full_name,
            left_at=None,
            is_counted=False,
            pending_until=pending_until,
            reject_reason=None,
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        # UNIQUE (invite_link_id, joined_user_tg_id) — poyga holatida yutildi.
        await session.rollback()
        logger.info(
            "record_join: UNIQUE violation — dublikat yutildi "
            "(invite_link_id=%s tg=%s)",
            invite_link.id,
            joined_user_tg_id,
        )
        return JoinResult(counted=False)

    await session.commit()
    logger.info(
        "record_join: yangi join pending (invite_link_id=%s tg=%s "
        "pending_until=%s)",
        invite_link.id,
        joined_user_tg_id,
        pending_until.isoformat(),
    )
    return JoinResult(
        counted=False,
        pending=True,
        inviter_tg_id=owner.telegram_id if owner is not None else None,
    )


async def _upsert_rejected(
    session: AsyncSession,
    *,
    invite_link_id: int,
    joined_user_tg_id: int,
    reason: str,
    joined_username: str | None = None,
    joined_full_name: str | None = None,
) -> None:
    """Rad etilgan join uchun audit yozuvi (is_counted=False, reject_reason)."""
    existing_stmt = select(InviteJoin).where(
        InviteJoin.invite_link_id == invite_link_id,
        InviteJoin.joined_user_tg_id == joined_user_tg_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        existing.is_counted = False
        existing.pending_until = None
        existing.reject_reason = reason
        if joined_username is not None:
            existing.joined_username = joined_username
        if joined_full_name is not None:
            existing.joined_full_name = joined_full_name
        return
    session.add(
        InviteJoin(
            invite_link_id=invite_link_id,
            joined_user_tg_id=joined_user_tg_id,
            joined_username=joined_username,
            joined_full_name=joined_full_name,
            left_at=None,
            is_counted=False,
            pending_until=None,
            reject_reason=reason,
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()


async def record_leave(
    session: AsyncSession,
    *,
    tracked_chat_tg_id: int,
    left_user_tg_id: int,
) -> None:
    """Foydalanuvchining chatdan chiqishini barcha mos InviteJoin'larda belgilaydi.

    Bitta foydalanuvchi bir vaqtda faqat bitta invite link orqali kelgan bo'ladi,
    lekin nazariy jihatdan bir necha yozuv bo'lishi mumkin (masalan, tarixiy
    migratsiyalardan) — barchasini yopamiz.

    T-022 · Grace period ichida chiqib ketilsa (`pending_until IS NOT NULL`),
    yozuv counted holatiga o'tmagan bo'ladi, shuning uchun join_count kamaymaydi
    — faqat `reject_reason='quick_leave'` qo'yiladi va `pending_until` tozalanadi
    (worker uni endi qayta ko'rmaydi).
    """
    stmt = (
        select(InviteJoin, InviteLink)
        .join(InviteLink, InviteJoin.invite_link_id == InviteLink.id)
        .join(TrackedChat, InviteLink.tracked_chat_id == TrackedChat.id)
        .where(
            TrackedChat.chat_id == tracked_chat_tg_id,
            InviteJoin.joined_user_tg_id == left_user_tg_id,
            InviteJoin.left_at.is_(None),
        )
    )
    rows = (await session.execute(stmt)).all()
    if not rows:
        logger.debug(
            "record_leave: mos aktiv InviteJoin topilmadi "
            "(chat_tg=%s tg=%s)",
            tracked_chat_tg_id,
            left_user_tg_id,
        )
        return

    now = datetime.now(TASHKENT_TZ)
    for join, invite_link in rows:
        was_counted = join.is_counted
        was_pending = join.pending_until is not None
        join.left_at = now
        join.is_counted = False
        join.pending_until = None
        if was_counted:
            await _decrement_join_count(session, invite_link.id)
        elif was_pending and join.reject_reason is None:
            join.reject_reason = "quick_leave"
    await session.commit()
    logger.info(
        "record_leave: %d ta InviteJoin yopildi (chat_tg=%s tg=%s)",
        len(rows),
        tracked_chat_tg_id,
        left_user_tg_id,
    )


async def _increment_join_count(session: AsyncSession, invite_link_id: int) -> None:
    """Atomik `UPDATE ... SET join_count = join_count + 1`."""
    await session.execute(
        update(InviteLink)
        .where(InviteLink.id == invite_link_id)
        .values(join_count=InviteLink.join_count + 1)
    )


async def _decrement_join_count(session: AsyncSession, invite_link_id: int) -> None:
    """Atomik `UPDATE ... SET join_count = join_count - 1` (0 dan pastga tushmaydi)."""
    await session.execute(
        update(InviteLink)
        .where(InviteLink.id == invite_link_id, InviteLink.join_count > 0)
        .values(join_count=InviteLink.join_count - 1)
    )
