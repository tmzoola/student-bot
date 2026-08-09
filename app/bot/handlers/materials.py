"""Bot orqali material yuklash flow.

Foydalanuvchi PDF/DOCX/TXT hujjatni chat'ga yuboradi. Fayl serverga
saqlanadi, `Material(status=uploaded)` yaratiladi va background task
(extract → chunk → AI generatsiya) ishga tushiriladi. Progress xabar
edit qilinib boradi. Yakunida "Testni ochish" inline WebApp tugmasi.

Menyudan `/materials` sahifasini ochish uchun ham inline tugma
qo'shiladi — bot bilan chatlashish orqali ham, WebApp orqali ham
material yuklash mumkin.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import db.session as db_session
from core.config import MEDIA_ROOT, settings
from models.material import Material, MaterialStatus
from models.material_chunk import MaterialChunk
from models.student_profile import StudentProfile
from models.telegram_user import TelegramUser
from services.materials.extract import (
    ALLOWED_MIMES,
    MAX_MATERIAL_SIZE,
    MIME_DOCX,
    MIME_PDF,
    MIME_TXT,
    ExtractError,
    extract_text,
)

logger = logging.getLogger(__name__)
router = Router(name="materials")


_EXT_BY_MIME = {
    MIME_PDF: ".pdf",
    MIME_DOCX: ".docx",
    MIME_TXT: ".txt",
}


def _materials_webapp_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Materiallarim (WebApp)",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/materials"),
                )
            ]
        ]
    )


def _open_generated_quiz_kb(material_id: int, quiz_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Testni ochish",
                    web_app=WebAppInfo(
                        url=f"{settings.WEBAPP_URL}/materials/{material_id}/quiz/{quiz_id}"
                    ),
                )
            ]
        ]
    )


async def _load_profile_by_tg(telegram_id: int) -> StudentProfile | None:
    async with db_session.session_factory() as s:
        return await s.scalar(
            select(StudentProfile)
            .options(selectinload(StudentProfile.telegram_user))
            .join(TelegramUser, TelegramUser.id == StudentProfile.telegram_user_id)
            .where(TelegramUser.telegram_id == telegram_id)
        )


def _resolve_ext(mime: str, file_name: str | None) -> str:
    ext = _EXT_BY_MIME.get(mime)
    if ext:
        return ext
    if file_name:
        suf = Path(file_name).suffix.lower()
        if suf in {".pdf", ".docx", ".txt"}:
            return suf
    return ""


# ─── /materials komandasi ───────────────────────────────────────────

@router.message(F.text.in_({"/materials", "📄 Material yuklash"}))
async def on_materials_cmd(msg: Message) -> None:
    profile = await _load_profile_by_tg(msg.from_user.id)
    if profile is None or not profile.is_approved:
        return
    await msg.answer(
        "PDF, DOCX yoki TXT hujjatni shu chatga yuboring — men undan test yarataman.\n"
        "Yoki WebApp'da materiallarni ko'ring:",
        reply_markup=_materials_webapp_kb(),
    )


# ─── Hujjat qabul qilish ────────────────────────────────────────────

@router.message(F.document)
async def on_document(msg: Message) -> None:
    profile = await _load_profile_by_tg(msg.from_user.id)
    if profile is None or not profile.is_approved:
        return

    doc = msg.document
    mime = doc.mime_type or ""
    if mime not in ALLOWED_MIMES:
        await msg.reply(
            "❌ Faqat PDF, DOCX yoki TXT fayllar qabul qilinadi.",
        )
        return
    if doc.file_size and doc.file_size > MAX_MATERIAL_SIZE:
        mb = MAX_MATERIAL_SIZE // (1024 * 1024)
        await msg.reply(f"❌ Fayl hajmi {mb} MB dan oshmasin.")
        return

    ext = _resolve_ext(mime, doc.file_name)
    if not ext:
        await msg.reply("❌ Fayl turini aniqlab bo'lmadi.")
        return

    # Fayl'ni saqlash
    target_dir = MEDIA_ROOT / "materials" / str(profile.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    storage_path = target_dir / filename

    try:
        from bot.setup import bot
        await bot.download(doc, destination=storage_path)
    except Exception as exc:
        logger.exception("Fayl yuklab olib bo'lmadi")
        await msg.reply(f"❌ Faylni yuklab bo'lmadi: {exc}")
        return

    size_bytes = storage_path.stat().st_size

    async with db_session.session_factory() as s:
        material = Material(
            student_profile_id=profile.id,
            title=doc.file_name or filename,
            filename=filename,
            mime=mime,
            size_bytes=size_bytes,
            storage_path=str(storage_path),
            status=MaterialStatus.uploaded,
        )
        s.add(material)
        await s.commit()
        await s.refresh(material)
        material_id = material.id

    progress = await msg.reply("📥 Yuklandi. Matn ajratilmoqda…")

    asyncio.create_task(
        _process_material(
            material_id=material_id,
            chat_id=msg.chat.id,
            progress_message_id=progress.message_id,
        )
    )


# ─── Background pipeline ────────────────────────────────────────────

async def _edit_progress(chat_id: int, message_id: int, text: str, kb=None) -> None:
    from bot.setup import bot
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=kb,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Progress xabarini edit qilib bo'lmadi")


async def _process_material(
    material_id: int, chat_id: int, progress_message_id: int
) -> None:
    """Extract → chunk → AI generatsiya (background)."""
    from services.materials.chunk import chunk_text
    from services.materials.generate import generate_quiz_for_material

    # 1. Extraction
    try:
        async with db_session.session_factory() as s:
            material = await s.get(Material, material_id)
            if material is None:
                return
            material.status = MaterialStatus.extracting
            await s.commit()
            path = material.storage_path
            mime = material.mime

        text = await asyncio.to_thread(extract_text, path, mime)
        if not text or not text.strip():
            raise ExtractError("Matn topilmadi (bo'sh yoki skanlangan PDF)")

        chunks = chunk_text(text, max_chars=2000)

        async with db_session.session_factory() as s:
            material = await s.get(Material, material_id)
            material.extracted_text_length = len(text)
            for i, chunk_str in enumerate(chunks):
                s.add(MaterialChunk(material_id=material_id, order=i, text=chunk_str))
            await s.commit()

        await _edit_progress(
            chat_id, progress_message_id, "🔎 Matn ajratildi. 🤖 Test yaratilmoqda…"
        )
    except Exception as exc:
        logger.exception("Extraction xatosi (material_id=%s)", material_id)
        async with db_session.session_factory() as s:
            m = await s.get(Material, material_id)
            if m is not None:
                m.status = MaterialStatus.failed
                m.error_message = str(exc)[:500]
                await s.commit()
        await _edit_progress(
            chat_id, progress_message_id, f"❌ Matn ajratib bo'lmadi: {exc}"
        )
        return

    # 2. AI generatsiya
    try:
        quiz = await generate_quiz_for_material(
            material_id=material_id, num_questions=10, difficulty="medium"
        )
    except Exception as exc:
        logger.exception("AI generatsiya xatosi (material_id=%s)", material_id)
        await _edit_progress(
            chat_id,
            progress_message_id,
            f"❌ Test yaratib bo'lmadi: {exc}",
        )
        return

    await _edit_progress(
        chat_id,
        progress_message_id,
        f"✅ Tayyor! {quiz.num_questions} ta savol yaratildi.",
        kb=_open_generated_quiz_kb(material_id, quiz.id),
    )


async def _process_material_no_chat(material_id: int) -> None:
    """WebApp upload uchun — extract + generatsiya, progress bot chatga
    yubormaydi (foydalanuvchi WebApp'da status polling qiladi)."""
    from services.materials.chunk import chunk_text
    from services.materials.generate import generate_quiz_for_material

    try:
        async with db_session.session_factory() as s:
            material = await s.get(Material, material_id)
            if material is None:
                return
            material.status = MaterialStatus.extracting
            await s.commit()
            path = material.storage_path
            mime = material.mime

        text = await asyncio.to_thread(extract_text, path, mime)
        if not text or not text.strip():
            raise ExtractError("Matn topilmadi (bo'sh yoki skanlangan PDF)")

        chunks = chunk_text(text, max_chars=2000)
        async with db_session.session_factory() as s:
            m = await s.get(Material, material_id)
            m.extracted_text_length = len(text)
            for i, chunk_str in enumerate(chunks):
                s.add(MaterialChunk(material_id=material_id, order=i, text=chunk_str))
            await s.commit()
    except Exception as exc:
        logger.exception("WebApp extraction xatosi (material_id=%s)", material_id)
        async with db_session.session_factory() as s:
            m = await s.get(Material, material_id)
            if m is not None:
                m.status = MaterialStatus.failed
                m.error_message = str(exc)[:500]
                await s.commit()
        return

    try:
        await generate_quiz_for_material(
            material_id=material_id, num_questions=10, difficulty="medium"
        )
    except Exception:
        logger.exception("WebApp AI generatsiya xatosi (material_id=%s)", material_id)
        # generate_quiz_for_material o'zi status = failed qiladi
