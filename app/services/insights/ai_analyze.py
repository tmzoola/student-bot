"""AI insight generatsiya (T-303).

`UserStats` va talaba profili asosida Claude Sonnet'dan strukturaviy
tavsiya oladi (tool use bilan). O'zbek tilida.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field

from core.config import settings
from models.student_profile import StudentProfile
from services.ai.base import AIProviderError
from services.insights.stats import UserStats

logger = logging.getLogger(__name__)


# ─── Result schema ───────────────────────────────────────────────────

@dataclass
class WeaknessItem:
    topic: str
    tip: str
    accuracy: int | None = None


@dataclass
class StrengthItem:
    topic: str
    accuracy: int | None = None


@dataclass
class InsightResult:
    summary: str
    weaknesses: list[WeaknessItem] = field(default_factory=list)
    strengths: list[StrengthItem] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "weaknesses": [asdict(w) for w in self.weaknesses],
            "strengths": [asdict(s) for s in self.strengths],
            "recommendations": list(self.recommendations),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "InsightResult":
        return cls(
            summary=str(d.get("summary", "")),
            weaknesses=[WeaknessItem(**w) for w in d.get("weaknesses", [])],
            strengths=[StrengthItem(**s) for s in d.get("strengths", [])],
            recommendations=[str(r) for r in d.get("recommendations", [])],
            input_tokens=int(d.get("input_tokens", 0)),
            output_tokens=int(d.get("output_tokens", 0)),
        )


# ─── Prompt / tool schema ────────────────────────────────────────────

INSIGHT_SYSTEM_PROMPT = """Sen — universitet talabasining o'quv jarayonini tahlil qiluvchi murabbiy assistentsan.
Vazifang: talabaning test urinishlari statistikasi asosida uning kuchli va zaif tomonlarini aniqlash,
har bir zaif mavzu uchun aniq maslahat, hamda kelasi hafta uchun bajariladigan tavsiyalar berish.

Qat'iy talablar:
1. Til: O'ZBEK. Rasmiy, ammo do'stona ohang.
2. Faqat berilgan statistikaga tayan — u yerda yo'q mavzular haqida taxmin qilma.
3. Har tavsiya AMALIY va O'LCHOVLI bo'lsin (masalan: "Mexanika mavzusiga 3 kun ichida 2 ta test yech").
4. Chiqishni FAQAT `submit_insight` tool orqali qaytar — matnli javob yozma.
5. Agar statistika juda kam bo'lsa — `summary` da shuni ochiq ayt va tavsiyalar sifatida "ko'proq test yechish" ni ber.
"""


INSIGHT_TOOL_SCHEMA: dict = {
    "name": "submit_insight",
    "description": "Talaba uchun tuzilgan tahlil natijasini qaytarish.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "2-3 gapdan iborat umumiy xulosa (o'zbek).",
                "minLength": 10,
                "maxLength": 1000,
            },
            "weaknesses": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "minLength": 1},
                        "tip": {"type": "string", "minLength": 1},
                        "accuracy": {"type": "integer"},
                    },
                    "required": ["topic", "tip"],
                    "additionalProperties": False,
                },
            },
            "strengths": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "minLength": 1},
                        "accuracy": {"type": "integer"},
                    },
                    "required": ["topic"],
                    "additionalProperties": False,
                },
            },
            "recommendations": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {"type": "string", "minLength": 1},
            },
        },
        "required": ["summary", "recommendations"],
        "additionalProperties": False,
    },
}


def _format_stats_for_prompt(stats: UserStats, profile: StudentProfile) -> str:
    fac = profile.faculty.name if profile.faculty else "—"
    lines = [
        f"Talaba: {profile.full_name}",
        f"Fakultet: {fac}, {profile.course_number}-kurs, {profile.semester}-semestr",
        "",
        f"Umumiy urinishlar: {stats.attempts_total}",
        f"Umumiy aniqlik: {stats.overall_accuracy_pct}%",
        "",
        "Mavzular bo'yicha (aniqlik %):",
    ]
    if not stats.by_topic:
        lines.append("— (yetarli ma'lumot yo'q)")
    else:
        for t in stats.by_topic[:15]:
            lines.append(
                f"— {t.topic_title} ({t.subject_name}): "
                f"{t.accuracy_pct}% ({t.correct}/{t.correct + t.wrong}, urinish: {t.attempts})"
            )
    lines.append("")
    lines.append("Fanlar bo'yicha:")
    if not stats.by_subject:
        lines.append("— (bo'sh)")
    else:
        for sb in stats.by_subject[:10]:
            lines.append(
                f"— {sb.subject_name}: {sb.accuracy_pct}% "
                f"({sb.correct}/{sb.correct + sb.wrong}, urinish: {sb.attempts})"
            )
    lines.append("")
    lines.append("So'nggi 4 hafta:")
    for tp in stats.recent_trend:
        lines.append(f"— {tp.week_start}: {tp.attempts} urinish, {tp.accuracy_pct}%")
    return "\n".join(lines)


# ─── Provider chaqiruvi ─────────────────────────────────────────────

async def generate_insight(
    stats: UserStats, profile: StudentProfile
) -> InsightResult:
    """Claude'dan strukturaviy tahlil oladi.

    Xato bo'lsa `AIProviderError` ko'tariladi.
    """
    if settings.AI_PROVIDER.lower() != "claude":
        raise AIProviderError(
            f"Insight faqat 'claude' provider bilan mavjud (joriy: {settings.AI_PROVIDER})"
        )
    if not settings.ANTHROPIC_API_KEY:
        raise AIProviderError("ANTHROPIC_API_KEY bo'sh")

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=90.0)
    user_prompt = _format_stats_for_prompt(stats, profile)

    try:
        response = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=2000,
            system=[
                {
                    "type": "text",
                    "text": INSIGHT_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[INSIGHT_TOOL_SCHEMA],
            tool_choice={"type": "tool", "name": "submit_insight"},
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Claude insight chaqiruv xatosi")
        raise AIProviderError(f"Claude insight xatosi: {exc}") from exc

    tool_input: dict | None = None
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "submit_insight":
            tool_input = block.input
            break
    if tool_input is None:
        raise AIProviderError("Claude submit_insight tool bloki qaytarmadi")

    usage = getattr(response, "usage", None)
    in_tok = int(getattr(usage, "input_tokens", 0) or 0)
    out_tok = int(getattr(usage, "output_tokens", 0) or 0)
    logger.info(
        "ai_call_cost provider=claude kind=insight model=%s input_tokens=%d output_tokens=%d",
        settings.AI_MODEL,
        in_tok,
        out_tok,
    )

    try:
        return InsightResult(
            summary=str(tool_input["summary"]),
            weaknesses=[
                WeaknessItem(
                    topic=str(w["topic"]),
                    tip=str(w["tip"]),
                    accuracy=int(w["accuracy"]) if w.get("accuracy") is not None else None,
                )
                for w in tool_input.get("weaknesses", [])
            ],
            strengths=[
                StrengthItem(
                    topic=str(s["topic"]),
                    accuracy=int(s["accuracy"]) if s.get("accuracy") is not None else None,
                )
                for s in tool_input.get("strengths", [])
            ],
            recommendations=[str(r) for r in tool_input.get("recommendations", [])],
            input_tokens=in_tok,
            output_tokens=out_tok,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Insight tool_input validate xatosi: %s", tool_input)
        raise AIProviderError(f"Yaroqsiz insight strukturasi: {exc}") from exc
