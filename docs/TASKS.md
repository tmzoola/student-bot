# Student-bot — Vazifalar reestri

Yagona haqiqat manbai. Yangi vazifa qo'shilganda ID ketma-ket, qayta ishlatilmaydi.
Statuslar: `todo`, `in_progress`, `done`, `blocked`.

Har bir sessiyani `CLAUDE.md` va shu faylni o'qish bilan boshlang.

---

## Loyiha holati (qisqacha)

Student-bot — universitet talabalari uchun mid-term va yakuniy imtihonlarga tayyorgarlik yordamchisi (Telegram bot + WebApp + Admin panel + AI taxlil).

Loyiha edu-bot template'idan ko'chirilgan va **hozirda katta refaktor bosqichida**: edu-bot merosi bo'lgan modullar (book, shop, contest, guard, landing, quote, menu, rewards, referral, module) olib tashlanmoqda va universitet domenidagi yangi modellar (Faculty → Subject → Topic → Quiz → Question, StudentProfile) yoziladi. Prod DB hali yo'q — migratsiyalar oxirida squash qilinadi.

**Stack:** Python 3.11, FastAPI 0.115, aiogram 3.15, SQLAlchemy 2.0 async, Alembic, starlette-admin, PostgreSQL 15, Redis 7, Docker Compose. Kelajakda AI provider abstraksiyasi (`app/services/ai/`).

---

## Bosqich 1 — Domen modellarini qayta yozish

Har bir vazifa **bitta commit** bo'lib bajariladi. Tartib qat'iy — bir-birini bloklaydi.

### T-101 · `docs/TASKS.md` ni student-bot rejasi bilan qayta yozish
- **Owner:** solutions-architect
- **Status:** done
- **Priority:** yuqori
- **Acceptance:**
  - [x] Edu-bot merosi bo'lgan vazifalar reestrdan olib tashlandi
  - [x] Refaktor bosqichi va yangi domen modeli hujjatlashtirildi
  - [x] Bosqich 1 ning T-102…T-111 vazifalari yozildi
- **Notes:** Kelajakdagi bosqichlar (bot auth flow, WebApp UI, AI service) alohida rejalashtiriladi.

### T-102 · Kontent modellarini o'chirish (book/shop/landing/quote/menu/rewards)
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-101
- **Acceptance:**
  - [x] `app/models/` dan: `book.py`, `shop.py`, `landing.py`, `quote.py`, `menu.py`, `rewards.py` o'chirildi
  - [x] `app/models/__init__.py` yangilangan
  - [x] Tegishli admin view (`app/admin/views/`), handler (`app/bot/handlers/`, `app/api/v1/`), template (`app/templates/`), repository, schema tozalandi
  - [x] `python -c "import app.main"` xatosiz o'tadi
- **Notes:** Migratsiyalar shu bosqichda tegilmaydi (T-111 da squash qilinadi). `router.py`, `webapp.py`, `admin_tools.py`, `admin/__init__.py` legacy kod bilan chuqur bog'langani uchun minimal stub'ga aylantirildi — kelajakda student-bot uchun qayta yoziladi.

### T-103 · Guard modulini o'chirish
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-102
- **Acceptance:**
  - [ ] `app/guard/` katalogi o'chirildi
  - [ ] `app/services/nsfw_detector.py` o'chirildi
  - [ ] `app/models/guard.py` o'chirildi
  - [ ] `.env.example`, `docker-compose.yml`, `requirements.txt` dan NudeNet/guard konfiguratsiyasi olib tashlandi
  - [ ] `app.main` import xatosiz

### T-104 · Contest modulini o'chirish
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-103
- **Acceptance:**
  - [ ] `app/models/contest.py` va bog'liq handler/admin/template/schema o'chirildi
  - [ ] `app.main` import xatosiz

### T-105 · Referral modulini o'chirish
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-104
- **Acceptance:**
  - [ ] `app/models/referral.py`, `referral_event.py` o'chirildi
  - [ ] `app/services/referral/` o'chirildi
  - [ ] Admin view, bot handler, `chat_member`/`my_chat_member` bog'liqliklari olib tashlandi
  - [ ] `app.main` import xatosiz

### T-106 · `Faculty` modeli + migratsiya
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-105
- **Acceptance:**
  - [ ] `app/models/faculty.py`: `Faculty(id, name, code unique, is_active, created_at, updated_at)`
  - [ ] `models/__init__.py` da registratsiya
  - [ ] Alembic autogenerate migratsiya yaratildi
  - [ ] `make migrate` xatosiz

### T-107 · `Subject` modeli (`course_number`, `semester`) + migratsiya
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-106
- **Acceptance:**
  - [ ] `app/models/subject.py`: `Subject(id, faculty_id FK, name, code, course_number 1..4, semester 1..2, description, is_active, created_at, updated_at)`
  - [ ] `CheckConstraint` `course_number in (1,2,3,4)`, `semester in (1,2)`
  - [ ] UNIQUE `(faculty_id, code)`
  - [ ] Alembic migratsiya
  - [ ] `Faculty.subjects` back-populates aloqasi

### T-108 · `Topic` va `Quiz` ni Subject ga moslash + migratsiya
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-107
- **Acceptance:**
  - [ ] `Topic` da `module_id` → `subject_id` (FK Subject)
  - [ ] `Quiz` da `module_id` olib tashlanadi, faqat `topic_id` qoladi
  - [ ] `app/models/module.py` o'chirildi
  - [ ] Bog'liq admin view, handler, schema, repository yangilandi
  - [ ] Alembic migratsiya

### T-109 · `StudentProfile` modeli + `TelegramUser` bog'lanishi + migratsiya
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-108
- **Acceptance:**
  - [ ] `app/models/student_profile.py`: `StudentProfile(id, telegram_user_id FK unique, student_id_number unique, full_name, faculty_id FK, course_number, semester, is_approved bool default False, approved_at nullable, approved_by nullable, created_at, updated_at)`
  - [ ] `TelegramUser.profile` back-populates 1:1
  - [ ] Alembic migratsiya

### T-110 · `Attempt` ni `student_profile_id` ga o'tkazish + migratsiya
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-109
- **Acceptance:**
  - [ ] `Attempt.telegram_user_id` → `student_profile_id` (FK StudentProfile)
  - [ ] Repository/service/handler yangilandi
  - [ ] Alembic migratsiya

### T-111 · Migratsiyalarni bitta `0001_initial.py` ga squash qilish
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-110
- **Acceptance:**
  - [ ] `app/migrations/versions/` tozalandi
  - [ ] Yangi `0001_initial.py` autogenerate qilindi va yangi domenning to'liq schemasini yaratadi
  - [ ] Bo'sh DB da `alembic upgrade head` xatosiz o'tadi
  - [ ] `alembic downgrade base` ham xatosiz

---

## Bosqich 2 — Bot auth va student flow (kelajakda)

Rejalashtirilishi kerak:
- Student ID kiritish FSM
- Admin approve dialog (`is_approved=True`)
- Fakultet/kurs/semester tanlash → mavjud fanlar ro'yxati
- Testni yechish (WebApp)
- Urinishlar tarixi va statistika

## Bosqich 3 — AI taxlil (kelajakda)

- `app/services/ai/` — provider abstraksiyasi (Claude, OpenAI)
- `.env` da `AI_PROVIDER`, kalitlar
- Talaba urinishlari asosida kuchli/zaif tomonlarni aniqlash
- Mavzular bo'yicha tavsiyalar

## Bosqich 4 — Deploy va CI/CD (kelajakda)

- Server: `13.140.165.210`, port `8002`
- Domain: `student-13-140-165-210.sslip.io` (yoki alohida)
- GitHub Actions workflow
- Backup strategiyasi

---

## Texnik qarz (kuzatib boriladigan)

- [ ] `tests/` bo'sh — CI yo'q
- [ ] `dump.sql` mavjud bo'lsa repo'dan olib tashlansin
- [ ] Pre-commit (ruff/black) sozlanmagan
- [ ] Type hints qisman (`repositories/`, `uow/` audit kerak)

---

**Joriy fokus:** T-101 (bu fayl) → T-102. Har bir vazifa alohida commit bilan bajariladi.
