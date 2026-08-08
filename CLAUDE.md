# CLAUDE.md — Student-bot orientatsiya hujjati

Bu hujjat Claude sessiyalari uchun. Har bir yangi ish boshlashdan oldin **avval shu faylni**, keyin `docs/TASKS.md` faylini o'qing.

## Loyiha maqsadi

Student-bot — universitet talabalari uchun mid-term va yakuniy imtihonlarga tayyorgarlik yordamchisi. Telegram bot + WebApp platformasi.

Asosiy imkoniyatlar:
- Fakultet → kurs → fan → mavzu bo'yicha tuzilgan test bankasi
- Testlarni yechish, urinishlar tarixi va statistika
- **AI taxlil** — talaba urinishlari asosida kuchli va zaif tomonlarini aniqlash, mavzular bo'yicha tavsiyalar berish
- Admin panel orqali kontent va talabalarni boshqarish

## Farqi edu-bot'dan

Bu loyiha [`edu-bot`](../edu-bot/) template'idan yaratilgan, lekin auditoriyasi va domen modeli boshqacha:

| | edu-bot | student-bot |
|---|---|---|
| Auditoriya | Bir insonning brendi (o'qituvchi) | Universitet talabalari |
| Auth | Ochiq (Telegram + telefon) | Student ID + admin tasdig'i |
| Kontent modeli | Modul → Mavzu → Test | Fakultet → Kurs → Fan → Mavzu → Test |
| Do'kon/kitob | Bor | Yo'q |
| AI | Yo'q | Bor (Claude/OpenAI) |
| Guard bot (NSFW) | Bor | Yo'q (kelajakda kerak bo'lsa) |

## Texnologiya stack (edu-bot bilan bir xil)

- Python 3.11, FastAPI 0.115, aiogram 3.15
- SQLAlchemy 2.0 async + asyncpg, Alembic
- starlette-admin (admin panel, o'zbek locale)
- PostgreSQL 15, Redis 7
- Jinja2 (WebApp + admin template'lari)
- Docker Compose deployment

Yangi:
- **AI provider abstraktsiyasi** — `app/services/ai/` (Claude va OpenAI'ni almashtiriladigan qilib)

## Loyiha strukturasi

Edu-bot bilan bir xil (`app/main.py`, `app/bot/`, `app/api/v1/`, `app/models/`, ...) — batafsil edu-bot CLAUDE.md ga qarang.

Farqli qismlari:
- `app/models/` — universitet domen modellari (University, Faculty, Course, Subject, StudentProfile, ...)
- `app/services/ai/` — AI provider'lar va analiz mantiqi
- `app/bot/router.py` — student ID kiritish + admin approve dialog

## Ishga tushirish

```bash
cp .env.example .env
# .env ichida SECRET_KEY, BOT_TOKEN, ADMIN_PASSWORD, AI_PROVIDER, API keys to'ldiring
make install
make migrate
make run
```

## Deployment

Server: **13.140.165.210** (edu-bot bilan bir xil Contabo VPS).
- Port: **8002** (edu-bot 8001, samandar_market 8000).
- Domain: hozircha yo'q, keyin `student-13-140-165-210.sslip.io` yoki alohida.
- CI/CD: GitHub Actions (edu-bot pattern), ammo alohida repo/workflow.

Batafsil deploy notes — `docs/DEPLOY_NOTES.md`.

## Kod konventsiyalari

Edu-bot bilan bir xil (yupqa handler'lar, `UowDependency` yoki `get_db()`, pydantic sxemalar, alembic autogenerate). Batafsil edu-bot CLAUDE.md ga qarang.

## Muhim hujjatlar

- `docs/TASKS.md` — joriy vazifalar (project-manager yangilaydi).
- `../edu-bot/CLAUDE.md` — asosiy pattern'lar va domen bo'yicha (fokusda bo'lmagan qismlar).

## Umumiy qoidalar

1. Har bir sessiyani `CLAUDE.md` va `docs/TASKS.md` ni o'qish bilan boshlang.
2. Kodda mavjud pattern'ga moslashing.
3. Sirlar faqat `.env` orqali.
4. Commit va PR xabarlari **o'zbek tilida**.
