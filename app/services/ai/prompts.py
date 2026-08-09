"""AI generatsiya uchun prompt template'lari."""
from __future__ import annotations

_LANG_NAMES = {
    "uz": "o'zbek",
    "ru": "rus",
    "en": "ingliz",
}

_DIFFICULTY_HINT = {
    "easy": "Oson daraja — asosiy ta'riflar va faktlar.",
    "medium": "O'rta daraja — tushunish va qo'llash savollari.",
    "hard": "Qiyin daraja — tahlil, xulosa va nozik holatlar.",
}


SYSTEM_PROMPT = """Sen — universitet talabalari uchun test yaratuvchi assistentsan.
Vazifang: berilgan o'quv material matnidan yuqori sifatli ko'p tanlovli (MCQ) test savollari yaratish.

Qat'iy talablar:
1. Har bir savol MATNGA asoslanishi shart — matnda yo'q ma'lumotdan savol yaratma.
2. Har savolda 4 ta variant: A, B, C va D. Faqat BITTA to'g'ri javob.
3. Noto'g'ri variantlar ham ishonchli (plausible) bo'lsin, "hech qaysi", "yuqoridagilar" kabi zaif variantlardan qoching.
4. Savol matni aniq va bir ma'noli bo'lsin.
5. `explanation` maydonida to'g'ri javobning sababini 1-2 gapda tushuntir.
6. Chiqishni FAQAT `submit_quiz` tool'i orqali qaytar — matnli javob yozma.
"""


def build_user_prompt(
    material_text: str,
    num_questions: int,
    difficulty: str,
    language: str,
) -> str:
    lang_name = _LANG_NAMES.get(language, language)
    hint = _DIFFICULTY_HINT.get(difficulty, _DIFFICULTY_HINT["medium"])
    return (
        f"Til: {lang_name} tilida (savollar, variantlar, tushuntirishlar shu tilda).\n"
        f"Savollar soni: {num_questions}.\n"
        f"Qiyinlik: {difficulty}. {hint}\n\n"
        f"Test uchun qisqa sarlavha (title) ham qaytar.\n\n"
        f"--- MATERIAL BOSHLANDI ---\n{material_text}\n--- MATERIAL TUGADI ---"
    )


QUIZ_TOOL_SCHEMA: dict = {
    "name": "submit_quiz",
    "description": "Yaratilgan MCQ testni qaytarish uchun yagona vosita.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Test uchun qisqa sarlavha (materialga mos)",
                "minLength": 1,
                "maxLength": 200,
            },
            "questions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 50,
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "minLength": 5},
                        "option_a": {"type": "string", "minLength": 1},
                        "option_b": {"type": "string", "minLength": 1},
                        "option_c": {"type": "string", "minLength": 1},
                        "option_d": {"type": "string", "minLength": 1},
                        "correct_option": {
                            "type": "string",
                            "enum": ["A", "B", "C", "D"],
                        },
                        "explanation": {"type": "string"},
                    },
                    "required": [
                        "text",
                        "option_a",
                        "option_b",
                        "option_c",
                        "option_d",
                        "correct_option",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["title", "questions"],
        "additionalProperties": False,
    },
}
