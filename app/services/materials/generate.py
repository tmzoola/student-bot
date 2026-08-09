"""Materialdan AI orqali test generatsiya qilish servisi.

Yuqori darajali flow:

1. `Material` DB'dan chunk'lari bilan yuklanadi (holati `generating` ga
   ko'chiriladi).
2. Chunk matnlari birlashtiriladi. Uzun bo'lsa ~200_000 belgigacha (taxminan
   50K token) qisqartiriladi — Claude context'iga sig'ishi va cost'ni
   ushlab turish uchun.
3. `get_ai_provider().generate_quiz(...)` chaqiriladi. Bir marta retry
   (5xx / timeout / vaqtinchalik xatolik uchun).
4. Natija bir tranzaksiyada `GeneratedQuiz` + N ta `GeneratedQuestion`
   sifatida yoziladi.
5. Xato holida `material.status = failed`, `error_message` yoziladi va
   exception qayta ko'tariladi.

Bu funksiya WebApp yoki bot background task ichida chaqiriladi.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

import db.session as db_session
from models.generated_question import GeneratedQuestion
from models.generated_quiz import GeneratedQuiz, QuizDifficulty
from models.material import Material, MaterialStatus
from models.question import CorrectOption
from services.ai import get_ai_provider
from services.ai.base import AIProviderError
from services.ai.schemas import QuizGenResult

logger = logging.getLogger(__name__)

# Claude 200K token limit — o'rtacha 4 char/token bo'yicha ~800K char.
# Amalda cost'ni tejash uchun ~50K token = ~200K char'ga qisqartiramiz.
MAX_CONTEXT_CHARS = 200_000


def _assemble_context(chunks_text: list[str]) -> str:
    joined = "\n\n".join(t for t in chunks_text if t)
    if len(joined) <= MAX_CONTEXT_CHARS:
        return joined
    # Oxirini olamiz — konspektlarda odatda xulosa/muhim qism oxirroqda
    # bo'ladi. Bosh qismini kesib, [...] belgi bilan tush ushlab turamiz.
    tail = joined[-MAX_CONTEXT_CHARS:]
    logger.info(
        "context qisqartirildi: original=%d, kept=%d chars",
        len(joined),
        len(tail),
    )
    return "[...matnning boshi qisqartirildi...]\n\n" + tail


async def _call_provider_with_retry(
    text: str,
    num_questions: int,
    difficulty: str,
    language: str,
) -> QuizGenResult:
    provider = get_ai_provider()
    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            return await provider.generate_quiz(
                text=text,
                num_questions=num_questions,
                difficulty=difficulty,
                language=language,
            )
        except AIProviderError as exc:
            last_err = exc
            logger.warning("AI generate_quiz urinish %d xatosi: %s", attempt, exc)
            if attempt == 1:
                await asyncio.sleep(2.0)
                continue
            raise
    # Uncaught yo'l — mantiqiy jihatdan bu yerga yetib bo'lmaydi.
    raise AIProviderError(str(last_err) if last_err else "noma'lum xato")


async def generate_quiz_for_material(
    material_id: int,
    num_questions: int = 10,
    difficulty: str = "medium",
    language: str = "uz",
) -> GeneratedQuiz:
    """Materialning matnidan MCQ test yaratadi va DB'ga yozadi.

    Muvaffaqiyatli tugasa `GeneratedQuiz` (savollari bilan) qaytaradi.
    Xato bo'lsa `material.status = failed` va `AIProviderError` (yoki
    boshqa exception) ko'tariladi — chaqiruvchi buni ushlaydi.
    """
    if num_questions < 1 or num_questions > 50:
        raise ValueError("num_questions 1..50 oralig'ida bo'lishi kerak")
    try:
        difficulty_enum = QuizDifficulty(difficulty)
    except ValueError as exc:
        raise ValueError(f"Noma'lum difficulty: {difficulty}") from exc

    # 1. Kontekstni yig'amiz.
    async with db_session.session_factory() as session:
        material = await session.scalar(
            select(Material)
            .options(selectinload(Material.chunks))
            .where(Material.id == material_id)
        )
        if material is None:
            raise ValueError(f"Material topilmadi: id={material_id}")

        material.status = MaterialStatus.generating
        material.error_message = None
        await session.commit()

        chunks_text = [c.text for c in material.chunks]
        student_profile_id = material.student_profile_id
        material_title = material.title

    context = _assemble_context(chunks_text)
    if not context.strip():
        async with db_session.session_factory() as session:
            m = await session.get(Material, material_id)
            if m is not None:
                m.status = MaterialStatus.failed
                m.error_message = "Matn bo'sh — testlar yaratib bo'lmadi"
                await session.commit()
        raise AIProviderError("Materialdan matn ajratib bo'lmadi (bo'sh)")

    # 2. AI provider (retry bilan).
    try:
        result = await _call_provider_with_retry(
            text=context,
            num_questions=num_questions,
            difficulty=difficulty,
            language=language,
        )
    except Exception as exc:
        logger.exception("AI generate_quiz muvaffaqiyatsiz (material_id=%s)", material_id)
        async with db_session.session_factory() as session:
            m = await session.get(Material, material_id)
            if m is not None:
                m.status = MaterialStatus.failed
                m.error_message = str(exc)[:500]
                await session.commit()
        raise

    # 3. DB'ga yozamiz (bir tranzaksiya).
    async with db_session.session_factory() as session:
        quiz = GeneratedQuiz(
            material_id=material_id,
            student_profile_id=student_profile_id,
            title=result.title or material_title,
            difficulty=difficulty_enum,
            language=language,
            num_questions=len(result.questions),
        )
        session.add(quiz)
        await session.flush()  # quiz.id kerak

        for i, q in enumerate(result.questions):
            session.add(
                GeneratedQuestion(
                    generated_quiz_id=quiz.id,
                    order=i,
                    text=q.text,
                    option_a=q.option_a,
                    option_b=q.option_b,
                    option_c=q.option_c,
                    option_d=q.option_d,
                    correct_option=CorrectOption(q.correct_option),
                    explanation=q.explanation,
                )
            )

        m = await session.get(Material, material_id)
        if m is not None:
            m.status = MaterialStatus.ready
            m.error_message = None

        await session.commit()
        await session.refresh(quiz)

        # Sav'ol'larni ham yuklab qaytaramiz (selectin lazy=selectin bo'lsa
        # avtomatik, ammo aniq bo'lishi uchun refresh options bilan).
        quiz = await session.scalar(
            select(GeneratedQuiz)
            .options(selectinload(GeneratedQuiz.questions))
            .where(GeneratedQuiz.id == quiz.id)
        )

    logger.info(
        "generated_quiz yaratildi: material_id=%s quiz_id=%s questions=%d tokens_in=%d tokens_out=%d",
        material_id,
        quiz.id if quiz else "?",
        len(result.questions),
        result.input_tokens,
        result.output_tokens,
    )
    return quiz  # type: ignore[return-value]
