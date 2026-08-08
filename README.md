# Muslima Darmonova — Edu Bot

Telegram Mini App + Admin Panel for an Uzbek educational platform. Users solve quizzes, track scores on a leaderboard, buy books, and participate in timed competitions — all inside Telegram. Admins manage content through a full-featured web panel.

## Features

### Bot
- Persistent reply keyboard with **Test ishlash** (opens Mini App), **Kitoblar do'koni**, **Ma'lumot**
- Daily quiz notifications
- Re-engagement notifications — users inactive for 3+ days get a personalized message at 10:00 Tashkent time
- Book shop: admin posts books with prices; users pay via card, admin confirms payment, bot collects delivery info via FSM, order tracking in Mini App

### Mini App (WebApp)
- Module → Topic → Quiz flow with a timer and score tracking
- Leaderboard (day / week / month / all-time)
- Daily quiz with a countdown to the next one
- Timed competitions (contests) with a live scoreboard
- Profile page with order history
- Dark mode, fully mobile-friendly

### Admin Panel (`/admin/`)
- **Test yaratish** — rich quiz builder: create/edit quizzes with bulk-paste support
- **Yutuqli testlar** — create and manage timed contest quizzes with winner boards and Excel export
- **Kitob yuklash** — upload PDF/EPUB books for in-app reading
- **Do'kon kitoblari** — manage shop books with cover image upload
- **Buyurtmalar boshqaruvi** — order management with confirm/ship actions that message the buyer
- **Reyting** — live leaderboard across all periods
- **Motivatsiya** — manage motivational quotes shown on the home screen
- **Xabar yuborish** — broadcast messages to all active users
- **Foydalanuvchilar** — user list with registration stats
- Consistent dark/light theme across all pages

## Tech Stack

| Layer        | Technology                                                  |
|--------------|-------------------------------------------------------------|
| Bot          | aiogram 3.x, aiogram FSM                                   |
| Web          | FastAPI + Jinja2 templates + uvicorn                       |
| Admin panel  | starlette-admin with custom template overrides              |
| Database     | PostgreSQL + SQLAlchemy 2.x async + asyncpg                |
| Migrations   | Alembic (async)                                             |
| Scheduling   | asyncio background task (lifespan)                         |
| Time zone    | `zoneinfo` — Asia/Tashkent (UTC+5)                        |
| Media        | Local filesystem (`/media/`), served as static files        |
| Deployment   | Docker Compose (db + app)                                   |

## Quick Start

```bash
git clone <repo-url> edu-bot
cd edu-bot

cp .env.example .env
# Fill in BOT_TOKEN, WEBAPP_URL, DATABASE_URL, etc.

docker compose up -d --build
```

After startup:
- **Mini App**: `WEBAPP_URL/webapp/`
- **Admin panel**: `http://localhost:8000/admin/`

### Rebuild after code changes

```bash
docker compose up -d --build
```

## Environment Variables

| Variable            | Purpose                                              |
|---------------------|------------------------------------------------------|
| `BOT_TOKEN`         | Telegram bot token from @BotFather                  |
| `WEBAPP_URL`        | Public HTTPS URL where the Mini App is served        |
| `DATABASE_URL`      | `postgresql+asyncpg://user:pass@host:port/db`        |
| `POSTGRES_USER`     | Postgres container user                              |
| `POSTGRES_PASSWORD` | Postgres container password                          |
| `POSTGRES_DB`       | Postgres database name                               |
| `ADMIN_USERNAME`    | Default admin login                                  |
| `ADMIN_PASSWORD`    | Default admin password                               |

## Project Layout

```
app/
├── main.py                  FastAPI app entrypoint, lifespan, re-engagement scheduler
├── bot/
│   └── router.py            aiogram handlers, FSM states, reply keyboard, shop flow
├── api/v1/
│   ├── webapp.py            Mini App pages + REST API (quizzes, leaderboard, orders…)
│   └── admin_tools.py       Custom admin tool endpoints (builder, shop, orders, …)
├── admin/
│   ├── __init__.py          starlette-admin setup, view registration
│   ├── views/               Per-model admin views (quiz, book, user, shop, …)
│   └── templates/           starlette-admin base.html override (theme, dark mode)
├── models/                  SQLAlchemy ORM models
├── migrations/              Alembic migration versions
├── services/
│   └── notifications.py     Re-engagement & daily quiz notification logic
├── templates/               Jinja2 HTML templates (Mini App + admin tools)
│   ├── admin_builder.html
│   ├── admin_shop_books.html
│   ├── admin_orders.html
│   └── …
└── db/
    └── session.py           Async engine + session factory
docker-compose.yml
Dockerfile
```

## Migrations

```bash
# Inside the container
docker exec -it malaka_app alembic upgrade head

# Or generate a new migration after model changes
docker exec -it malaka_app alembic revision --autogenerate -m "description"
```

## Notes

- All money amounts are stored as integer UZS — no floats.
- Day boundaries for leaderboard/reports use Tashkent local time (UTC+5).
- Re-engagement notifications fire once daily at 10:00 Tashkent time via an asyncio loop; the scheduler runs inside the FastAPI lifespan, no Celery needed.
- The shop order FSM state is set programmatically from the admin panel (via `StorageKey` + `FSMContext`) so the bot picks up delivery info collection immediately after admin confirms payment.
- Media files (book covers, question images) are stored under `MEDIA_ROOT` and served at `/media/`.
