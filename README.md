# Student Bot

Universitet talabalari uchun mid-term va yakuniy imtihonlarga tayyorgarlik yordamchisi. Telegram bot orqali ro'yxatdan o'tib, WebApp'da fakultet/kurs/semestrga mos test bankasidan foydalanish, urinishlar tarixi va statistika, admin tomonidan kontent boshqaruvi.

## Asosiy imkoniyatlar

### Bot
- **Ro'yxatdan o'tish FSM** — student ID → F.I.Sh → fakultet → kurs → semestr
- **Admin approve/reject** — yangi ariza admin chat'iga inline tugma bilan yuboriladi
- **Reg-gate middleware** — ro'yxatsizlar va tasdiqlanmaganlar cheklangan
- **Asosiy menyu** — Fanlar (WebApp), Profil, Statistika

### WebApp
- **Fanlar ro'yxati** — foydalanuvchi profiliga mos (fakultet/kurs/semestr filtri)
- **Fan → mavzular → testlar** navigatsiyasi
- **Test yechish** — timer, savol-javob, submit; correct answer serverdan chiqmaydi
- **Profil** — urinishlar tarixi, o'rtacha ball, statistika
- Telegram WebApp `initData` validation (HMAC-SHA256)

### Admin panel (`/admin/`)
- **Universitet** — Fakultetlar, Fanlar
- **Kontent** — Mavzular, Testlar, Savollar
- **Foydalanuvchilar** — Talaba profillari (approve, ban), Telegram foydalanuvchilar

## Domen modeli

```
Faculty ──► Subject (course_number 1..4, semester 1..2) ──► Topic ──► Quiz ──► Question
                                                                           ▲
TelegramUser ◄── 1:1 ── StudentProfile ─────── QuizAttempt ────────────────┘
                        (is_approved)
```

## Stack

| Qatlam        | Texnologiya                                        |
|---------------|----------------------------------------------------|
| Bot           | aiogram 3.15, Redis FSM storage                    |
| Web           | FastAPI 0.115 + Jinja2 + uvicorn                   |
| Admin panel   | starlette-admin (o'zbek locale)                    |
| Database      | PostgreSQL 15 + SQLAlchemy 2.0 async + asyncpg     |
| Migratsiya    | Alembic (async)                                    |
| Kesh/FSM      | Redis 7                                            |
| Vaqt zonasi   | Asia/Tashkent (UTC+5)                              |
| Deploy        | Docker Compose + nginx + certbot                   |
| Monitoring    | Grafana + Loki + Promtail + Dozzle                 |

## Ishga tushirish (lokal)

```bash
git clone <repo-url> student-bot
cd student-bot

cp .env.example .env
# .env ichida SECRET_KEY, BOT_TOKEN, ADMIN_PASSWORD, ADMIN_CHAT_ID to'ldiring

make install          # pip install -r requirements.txt
make migrate          # alembic upgrade head
make run              # cd app && uvicorn main:app --reload --port 8000
```

Docker orqali:

```bash
docker compose up -d --build
```

Ishga tushgach:
- **WebApp**: `WEBAPP_URL/`
- **Admin panel**: `http://localhost:8002/admin/`

## Muhit o'zgaruvchilari (asosiy)

| O'zgaruvchi          | Vazifasi                                             |
|----------------------|------------------------------------------------------|
| `SECRET_KEY`         | Session cookie va CSRF uchun                         |
| `BOT_TOKEN`          | @BotFather'dan olingan token                         |
| `BOT_USERNAME`       | Bot username (`@` siz) — deep-link uchun             |
| `WEBAPP_URL`         | Public HTTPS URL (Telegram WebApp uchun)             |
| `ADMIN_CHAT_ID`      | Ro'yxatdan o'tish arizasi yuboriladigan chat         |
| `POSTGRES_*`         | DB user/password/host/db                             |
| `ADMIN_USERNAME`     | Admin panel login                                    |
| `ADMIN_PASSWORD`     | Admin panel parol                                    |
| `REDIS_URL`          | Redis (FSM storage + kesh)                           |
| `GRAFANA_ADMIN_*`    | Grafana admin credentials                            |

To'liq ro'yxat — `.env.example` da.

## Loyiha strukturasi

```
app/
├── main.py                 FastAPI entrypoint, lifespan
├── bot/
│   ├── setup.py            Dispatcher, Redis storage, router include
│   ├── router.py           /start, minimal handler'lar
│   ├── middlewares.py      Blacklist + RegistrationGate
│   └── handlers/
│       ├── registration.py Ro'yxatdan o'tish FSM
│       ├── admin_approval.py  Approve/reject callback flow
│       └── menu.py         Fanlar/Profil/Statistika
├── api/v1/
│   ├── student.py          WebApp REST API (fanlar, quiz submit, profil)
│   └── webapp.py           WebApp HTML sahifalar
├── admin/                  starlette-admin view'lar
├── models/                 SQLAlchemy modellari
│   ├── faculty.py subject.py topic.py quiz.py question.py
│   ├── student_profile.py telegram_user.py attempt.py
├── migrations/versions/    Alembic (bitta initial)
├── templates/              Jinja2 (subjects, subject_detail, quiz, profile, ...)
├── utils/webapp_auth.py    Telegram WebApp initData HMAC validation
└── db/session.py           Async engine + session factory

deploy/
├── nginx/student-bot.conf  Reverse proxy + TLS + subpath
└── scripts/backup.sh       Kunlik pg_dump + media backup

docs/
├── TASKS.md                Vazifalar reestri
└── DEPLOY_NOTES.md         Deploy qo'llanmasi
```

## Testlar

```bash
pip install -r requirements-dev.txt
pytest -q
```

Testlar `aiosqlite` bilan ishlaydi (Postgres shart emas). Qamrov:
- Ro'yxatdan o'tish (StudentProfile constraint'lari)
- Quiz submit — score hisoblash, correct_option yashirinligi

## Migratsiyalar

```bash
# Yangi migratsiya autogenerate
alembic revision --autogenerate -m "description"

# Upgrade/downgrade
alembic upgrade head
alembic downgrade -1
```

Yoki Docker ichida:

```bash
docker compose exec app alembic upgrade head
```

## Deploy

Server: **13.140.165.210**, domain: **student-13-140-165-210.sslip.io**, port: **8002**.

Batafsil qo'llanma — [`docs/DEPLOY_NOTES.md`](docs/DEPLOY_NOTES.md). Qisqacha:

1. Serverda `docker`, `nginx`, `certbot` o'rnatish + `deploy` foydalanuvchisi
2. `git clone` `/opt/student-bot`, `.env` to'ldirish
3. `docker compose up -d --build`
4. Nginx config + `certbot --nginx -d student-13-140-165-210.sslip.io`
5. GitHub Secrets: `SSH_HOST`, `SSH_USER`, `SSH_KEY`, `DEPLOY_PATH`
6. Crontab: kunlik backup

Yangilanish avtomatik — `main` branch'ga push → GitHub Actions SSH deploy.

## Muhim eslatmalar

- **Kod konventsiyasi** — CLAUDE.md ga qarang
- **Yupqa handler'lar** — biznes mantiq `services/` da
- **Vaqt zonasi** — hamma sanalar `Asia/Tashkent`
- **Sirlar** — faqat `.env` orqali, hech qachon commit qilinmaydi
- **Commit va PR xabarlari o'zbek tilida**

## Hujjatlar

- [`CLAUDE.md`](CLAUDE.md) — Claude sessiyalari uchun orientatsiya
- [`docs/TASKS.md`](docs/TASKS.md) — joriy va bajarilgan vazifalar
- [`docs/DEPLOY_NOTES.md`](docs/DEPLOY_NOTES.md) — deploy va monitoring qo'llanmasi
