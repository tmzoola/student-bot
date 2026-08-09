"""Talaba urinishlaridan statistika hisoblash (T-301).

Ikki manba:
- `QuizAttempt` — kanonik test bankasi (Quiz → Topic → Subject → Faculty)
- `GeneratedQuizAttempt` — AI generatsiya qilingan testlar (Material asosida)

Har ikkisida `answers JSON` bor. Aniqlikni har savol bo'yicha emas, urinish
darajasidagi `score / total` orqali baholaymiz — bu `answers` sxemasidan
qat'i nazar ishonchli.

`GeneratedQuiz` da Topic yo'q — Material sarlavhasi (`Material.title`)
virtual "topic" sifatida ishlatiladi. Ular subject sifatida "AI materiallar"
umumiy guruhga tushadi.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.attempt import QuizAttempt
from models.generated_attempt import GeneratedQuizAttempt
from models.generated_quiz import GeneratedQuiz
from models.material import Material
from models.quiz import Quiz
from models.subject import Subject
from models.topic import Topic


# ─── Data classes ────────────────────────────────────────────────────

@dataclass
class TopicStat:
    topic_id: int | None  # None — AI Material'lari uchun
    topic_title: str
    subject_name: str
    attempts: int
    correct: int
    wrong: int
    accuracy_pct: int


@dataclass
class SubjectStat:
    subject_id: int | None
    subject_name: str
    attempts: int
    correct: int
    wrong: int
    accuracy_pct: int


@dataclass
class TrendPoint:
    week_start: str  # ISO date (YYYY-MM-DD)
    attempts: int
    accuracy_pct: int


@dataclass
class UserStats:
    attempts_total: int
    overall_accuracy_pct: int
    by_topic: list[TopicStat] = field(default_factory=list)
    by_subject: list[SubjectStat] = field(default_factory=list)
    recent_trend: list[TrendPoint] = field(default_factory=list)
    top_weaknesses: list[TopicStat] = field(default_factory=list)
    top_strengths: list[TopicStat] = field(default_factory=list)


# ─── Helpers ─────────────────────────────────────────────────────────

_AI_SUBJECT = "AI materiallar"


def _pct(correct: int, total: int) -> int:
    if total <= 0:
        return 0
    # Float shovqinini oldini olish uchun integer arifmetikada yaxlitlash:
    # (correct*100 + total//2) // total = matematik "round half up".
    return (correct * 100 + total // 2) // total


def _week_start(dt: datetime) -> datetime:
    # Dushanbadan boshlaymiz (ISO haftasi).
    dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    d = dt.date()
    monday = d - timedelta(days=d.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


# ─── Loaders ─────────────────────────────────────────────────────────

async def _load_canonical(
    db: AsyncSession, profile_id: int
) -> list[tuple[QuizAttempt, Quiz, Topic, Subject]]:
    stmt = (
        select(QuizAttempt, Quiz, Topic, Subject)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .join(Topic, Topic.id == Quiz.topic_id)
        .join(Subject, Subject.id == Topic.subject_id)
        .where(QuizAttempt.student_profile_id == profile_id)
    )
    rows = (await db.execute(stmt)).all()
    return [(a, q, t, s) for a, q, t, s in rows]


async def _load_generated(
    db: AsyncSession, profile_id: int
) -> list[tuple[GeneratedQuizAttempt, GeneratedQuiz, Material]]:
    stmt = (
        select(GeneratedQuizAttempt, GeneratedQuiz, Material)
        .join(GeneratedQuiz, GeneratedQuiz.id == GeneratedQuizAttempt.generated_quiz_id)
        .join(Material, Material.id == GeneratedQuiz.material_id)
        .where(GeneratedQuizAttempt.student_profile_id == profile_id)
    )
    rows = (await db.execute(stmt)).all()
    return [(a, q, m) for a, q, m in rows]


# ─── Aggregation ─────────────────────────────────────────────────────

def _agg_topics(
    canonical: list[tuple[QuizAttempt, Quiz, Topic, Subject]],
    generated: list[tuple[GeneratedQuizAttempt, GeneratedQuiz, Material]],
) -> list[TopicStat]:
    """Topic bo'yicha yig'ma. Kanonik va AI Material alohida kalitlar."""
    acc: dict[tuple[str, int | None], dict[str, int | str]] = {}

    def bump(key: tuple[str, int | None], title: str, subject: str, score: int, total: int) -> None:
        d = acc.setdefault(
            key,
            {"attempts": 0, "correct": 0, "wrong": 0, "title": title, "subject": subject},
        )
        d["attempts"] = int(d["attempts"]) + 1  # type: ignore[arg-type]
        d["correct"] = int(d["correct"]) + score  # type: ignore[arg-type]
        d["wrong"] = int(d["wrong"]) + max(0, total - score)  # type: ignore[arg-type]

    for a, _q, t, s in canonical:
        bump(("q", t.id), t.title, s.name, a.score, a.total)
    for a, gq, m in generated:
        # AI material title'ni "topic" sifatida ishlatamiz. topic_id yo'q — 0
        # bilan farqlash uchun manba prefiksi kalitda.
        bump(("m", m.id), m.title, _AI_SUBJECT, a.score, a.total)

    out: list[TopicStat] = []
    for (kind, ident), d in acc.items():
        attempts = int(d["attempts"])  # type: ignore[arg-type]
        if attempts < 2:
            continue
        correct = int(d["correct"])  # type: ignore[arg-type]
        wrong = int(d["wrong"])  # type: ignore[arg-type]
        total = correct + wrong
        out.append(
            TopicStat(
                topic_id=ident if kind == "q" else None,
                topic_title=str(d["title"]),
                subject_name=str(d["subject"]),
                attempts=attempts,
                correct=correct,
                wrong=wrong,
                accuracy_pct=_pct(correct, total),
            )
        )
    out.sort(key=lambda x: (-x.attempts, x.topic_title))
    return out


def _agg_subjects(
    canonical: list[tuple[QuizAttempt, Quiz, Topic, Subject]],
    generated: list[tuple[GeneratedQuizAttempt, GeneratedQuiz, Material]],
) -> list[SubjectStat]:
    acc: dict[tuple[str, int | None], dict[str, int | str]] = {}

    def bump(key: tuple[str, int | None], name: str, score: int, total: int) -> None:
        d = acc.setdefault(key, {"attempts": 0, "correct": 0, "wrong": 0, "name": name})
        d["attempts"] = int(d["attempts"]) + 1  # type: ignore[arg-type]
        d["correct"] = int(d["correct"]) + score  # type: ignore[arg-type]
        d["wrong"] = int(d["wrong"]) + max(0, total - score)  # type: ignore[arg-type]

    for a, _q, _t, s in canonical:
        bump(("s", s.id), s.name, a.score, a.total)
    for a, _gq, _m in generated:
        bump(("ai", None), _AI_SUBJECT, a.score, a.total)

    out: list[SubjectStat] = []
    for (kind, ident), d in acc.items():
        attempts = int(d["attempts"])  # type: ignore[arg-type]
        correct = int(d["correct"])  # type: ignore[arg-type]
        wrong = int(d["wrong"])  # type: ignore[arg-type]
        out.append(
            SubjectStat(
                subject_id=ident if kind == "s" else None,
                subject_name=str(d["name"]),
                attempts=attempts,
                correct=correct,
                wrong=wrong,
                accuracy_pct=_pct(correct, correct + wrong),
            )
        )
    out.sort(key=lambda x: (-x.attempts, x.subject_name))
    return out


def _agg_trend(
    canonical: list[tuple[QuizAttempt, Quiz, Topic, Subject]],
    generated: list[tuple[GeneratedQuizAttempt, GeneratedQuiz, Material]],
) -> list[TrendPoint]:
    """So'nggi 4 hafta bo'yicha kunlik/haftalik o'rtacha aniqlik.

    Bizda haftalik guruhlaymiz (4 nuqta) — kunlik shovqinsiz.
    """
    now = datetime.now(timezone.utc)
    start = _week_start(now - timedelta(weeks=3))
    weeks: dict[datetime, dict[str, int]] = {}
    for i in range(4):
        wk = start + timedelta(weeks=i)
        weeks[wk] = {"attempts": 0, "correct": 0, "total": 0}

    def add(dt: datetime | None, score: int, total: int) -> None:
        if dt is None:
            return
        ws = _week_start(dt)
        if ws not in weeks:
            return
        weeks[ws]["attempts"] += 1
        weeks[ws]["correct"] += score
        weeks[ws]["total"] += total

    for a, *_ in canonical:
        add(a.completed_at, a.score, a.total)
    for a, *_ in generated:
        add(a.completed_at, a.score, a.total)

    out: list[TrendPoint] = []
    for ws in sorted(weeks.keys()):
        d = weeks[ws]
        out.append(
            TrendPoint(
                week_start=ws.date().isoformat(),
                attempts=d["attempts"],
                accuracy_pct=_pct(d["correct"], d["total"]),
            )
        )
    return out


# ─── Public API ──────────────────────────────────────────────────────

async def compute_user_stats(
    db: AsyncSession, student_profile_id: int
) -> UserStats:
    canonical = await _load_canonical(db, student_profile_id)
    generated = await _load_generated(db, student_profile_id)

    attempts_total = len(canonical) + len(generated)
    correct_sum = sum(a.score for a, *_ in canonical) + sum(a.score for a, *_ in generated)
    total_sum = sum(a.total for a, *_ in canonical) + sum(a.total for a, *_ in generated)
    overall = _pct(correct_sum, total_sum)

    by_topic = _agg_topics(canonical, generated)
    by_subject = _agg_subjects(canonical, generated)
    trend = _agg_trend(canonical, generated)

    # Top zaif/kuchli — faqat 2+ urinishga ega mavzular ichidan.
    weaknesses = sorted(by_topic, key=lambda x: (x.accuracy_pct, -x.attempts))[:5]
    strengths = sorted(by_topic, key=lambda x: (-x.accuracy_pct, -x.attempts))[:5]

    return UserStats(
        attempts_total=attempts_total,
        overall_accuracy_pct=overall,
        by_topic=by_topic,
        by_subject=by_subject,
        recent_trend=trend,
        top_weaknesses=weaknesses,
        top_strengths=strengths,
    )
