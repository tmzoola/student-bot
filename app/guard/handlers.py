import datetime as dt
import logging
import os
import shutil
import tempfile
import uuid

from aiogram import Bot, Router
from aiogram.filters import ChatMemberUpdatedFilter, Command, JOIN_TRANSITION
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from core.config import MEDIA_ROOT, settings
from db.session import session_factory
from models.base import TASHKENT_TZ
from models.guard import FlaggedUser, JoinEvent
from services.nsfw_detector import bio_flagged_words, image_nsfw_score

logger = logging.getLogger(__name__)
router = Router()


class ModAction(CallbackData, prefix="guard"):
    action: str  # "ban" | "ignore"
    chat_id: int
    user_id: int
    flag_id: int


def _save_photo_to_media(photo_path: str) -> str:
    """Vaqtinchalik rasmni media papkaga ko'chiradi, /media URL yo'lini qaytaradi."""
    guard_dir = MEDIA_ROOT / "guard"
    guard_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{uuid.uuid4().hex}.jpg"
    shutil.copy(photo_path, guard_dir / fname)
    return f"/media/guard/{fname}"


async def _download_profile_photo(bot: Bot, user_id: int) -> str | None:
    photos = await bot.get_user_profile_photos(user_id, limit=1)
    if not photos.total_count:
        return None
    file_id = photos.photos[0][-1].file_id  # eng katta o'lcham
    tg_file = await bot.get_file(file_id)
    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    await bot.download_file(tg_file.file_path, destination=path)
    return path


@router.message(Command("testme"))
async def cmd_testme(message: Message, bot: Bot):
    """Test komandasi (faqat admin): butun zanjirni o'z profilingizda sinaydi."""
    if message.from_user.id != settings.GUARD_ADMIN_CHAT_ID:
        return
    user = message.from_user
    reasons: list[str] = []
    nsfw_score = 0.0
    photo_path = await _download_profile_photo(bot, user.id)
    if photo_path:
        nsfw_score = image_nsfw_score(photo_path, 0.0) or 0.0  # 0.0 = eng yuqori ballni ko'rsatish
        reasons.append(f"🖼 Rasm eng yuqori ball: {nsfw_score:.0%}")
    else:
        reasons.append("🖼 Profil rasmi yo'q")
    try:
        full = await bot.get_chat(user.id)
        bio = getattr(full, "bio", None)
        hits = bio_flagged_words(bio)
        reasons.append(f"📝 Bio: {bio!r} → topilgan: {hits or 'yo`q'}")
    except Exception as e:
        reasons.append(f"📝 Bio olinmadi: {e}")

    media_url = _save_photo_to_media(photo_path) if photo_path else None
    async with session_factory() as session:
        row = FlaggedUser(
            user_id=user.id, username=user.username, full_name=user.full_name,
            chat_id=message.chat.id, chat_title="[TEST]", nsfw_score=nsfw_score,
            reasons=" | ".join(reasons), photo_path=media_url,
        )
        session.add(row)
        await session.commit()
        flag_id = row.id

    await _notify_admin(bot, message.chat.id, "[TEST]", user, reasons, photo_path, flag_id)
    if photo_path:
        os.remove(photo_path)


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def on_new_member(event: ChatMemberUpdated, bot: Bot):
    user = event.new_chat_member.user
    chat = event.chat
    logger.info("Yangi a'zo: %s (id=%s) chat=%s", user.full_name, user.id, chat.title)
    if user.is_bot:
        return

    reasons: list[str] = []
    nsfw_score = 0.0
    photo_path: str | None = None

    try:
        photo_path = await _download_profile_photo(bot, user.id)
        if photo_path:
            nsfw_score = image_nsfw_score(photo_path, settings.NSFW_THRESHOLD)
            if nsfw_score:
                reasons.append(f"🖼 Profil rasmi 18+ ({nsfw_score:.0%})")
    except Exception:
        logger.exception("Profil rasmini tekshirishda xato")

    try:
        full = await bot.get_chat(user.id)
        hits = bio_flagged_words(getattr(full, "bio", None))
        if hits:
            reasons.append("📝 Bio: " + ", ".join(hits))
    except Exception:
        logger.debug("Bio olinmadi: user=%s", user.id)

    # Har bir qo'shilishni jurnalga yozamiz (toza bo'lsa ham)
    async with session_factory() as session:
        session.add(JoinEvent(
            user_id=user.id, username=user.username, full_name=user.full_name,
            chat_id=chat.id, chat_title=chat.title, has_photo=photo_path is not None,
            nsfw_score=nsfw_score, flagged=bool(reasons),
        ))
        await session.commit()

    if not reasons:
        if photo_path:
            os.remove(photo_path)
        return

    media_url = _save_photo_to_media(photo_path) if photo_path else None
    async with session_factory() as session:
        row = FlaggedUser(
            user_id=user.id, username=user.username, full_name=user.full_name,
            chat_id=chat.id, chat_title=chat.title, nsfw_score=nsfw_score,
            reasons=" | ".join(reasons), photo_path=media_url,
        )
        session.add(row)
        await session.commit()
        flag_id = row.id

    logger.info("Flag #%s: user=%s chat=%s", flag_id, user.id, chat.id)
    await _notify_admin(bot, chat.id, chat.title or str(chat.id), user, reasons, photo_path, flag_id)
    if photo_path:
        os.remove(photo_path)


async def _notify_admin(bot, chat_id, chat_title, user, reasons, photo_path, flag_id):
    mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    text = (
        f"⚠️ <b>Shubhali profil aniqlandi</b> (#{flag_id})\n\n"
        f"👤 {mention} (<code>{user.id}</code>)\n"
        f"💬 Guruh: {chat_title}\n\n"
        "Sabab:\n• " + "\n• ".join(reasons)
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚫 Ban",
            callback_data=ModAction(action="ban", chat_id=chat_id, user_id=user.id, flag_id=flag_id).pack(),
        ),
        InlineKeyboardButton(
            text="✅ E'tiborsiz",
            callback_data=ModAction(action="ignore", chat_id=chat_id, user_id=user.id, flag_id=flag_id).pack(),
        ),
    ]])
    if photo_path:
        await bot.send_photo(settings.GUARD_ADMIN_CHAT_ID, FSInputFile(photo_path), caption=text, reply_markup=kb)
    else:
        await bot.send_message(settings.GUARD_ADMIN_CHAT_ID, text, reply_markup=kb)


@router.callback_query(ModAction.filter())
async def on_mod_action(query: CallbackQuery, callback_data: ModAction, bot: Bot):
    who = query.from_user.full_name
    action = None
    if callback_data.action == "ban":
        try:
            await bot.ban_chat_member(callback_data.chat_id, callback_data.user_id)
            result = "🚫 Foydalanuvchi ban qilindi."
            action = "banned"
        except Exception as e:
            result = f"❌ Ban qilib bo'lmadi: {e}"
    else:
        result = "✅ E'tiborsiz qoldirildi."
        action = "ignored"

    if action:
        async with session_factory() as session:
            row = await session.get(FlaggedUser, callback_data.flag_id)
            if row:
                row.action = action
                row.decided_by = who
                row.decided_at = dt.datetime.now(TASHKENT_TZ)
                await session.commit()

    await query.answer()
    suffix = f"\n\n<b>{result}</b> — {who}"
    if query.message.caption is not None:
        await query.message.edit_caption(caption=query.message.caption + suffix)
    else:
        await query.message.edit_text(query.message.text + suffix)
