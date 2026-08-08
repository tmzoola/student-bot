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
- **Status:** done
- **Depends on:** T-102
- **Acceptance:**
  - [x] `app/guard/` katalogi o'chirildi
  - [x] `app/services/nsfw_detector.py` o'chirildi
  - [x] `app/models/guard.py` o'chirildi
  - [x] `.env.example`, `docker-compose.yml`, `requirements.txt` dan NudeNet/guard konfiguratsiyasi olib tashlandi
  - [x] `app.main` import xatosiz

### T-104 · Contest modulini o'chirish
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-103
- **Acceptance:**
  - [x] `app/models/contest.py` va bog'liq handler/admin/template/schema o'chirildi
  - [x] `app.main` import xatosiz

### T-105 · Referral modulini o'chirish
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-104
- **Acceptance:**
  - [x] `app/models/referral.py`, `referral_event.py` o'chirildi
  - [x] `app/services/referral/` o'chirildi
  - [x] Admin view, bot handler, `chat_member`/`my_chat_member` bog'liqliklari olib tashlandi
  - [x] `app.main` import xatosiz

### T-106 · `Faculty` modeli + migratsiya
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-105
- **Acceptance:**
  - [x] `app/models/faculty.py`: `Faculty(id, name, code unique, is_active, created_at, updated_at)`
  - [x] `models/__init__.py` da registratsiya
  - [ ] ~~Alembic autogenerate migratsiya~~ — T-111 da bitta initial'ga squash qilinadi
  - [ ] ~~`make migrate`~~ — T-111 da tekshiriladi

### T-107 · `Subject` modeli (`course_number`, `semester`) + migratsiya
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-106
- **Acceptance:**
  - [x] `app/models/subject.py`: `Subject(id, faculty_id FK, name, code, course_number 1..4, semester 1..2, description, is_active, created_at, updated_at)`
  - [x] `CheckConstraint` `course_number in (1,2,3,4)`, `semester in (1,2)`
  - [x] UNIQUE `(faculty_id, code)`
  - [ ] ~~Alembic migratsiya~~ — T-111 da squash
  - [x] `Faculty.subjects` back-populates aloqasi

### T-108 · `Topic` va `Quiz` ni Subject ga moslash + migratsiya
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-107
- **Acceptance:**
  - [x] `Topic` da `module_id` → `subject_id` (FK Subject, CASCADE)
  - [x] `Quiz` da `module_id` olib tashlanadi, faqat `topic_id` qoladi (CASCADE)
  - [x] `app/models/module.py` va `app/admin/views/module.py` o'chirildi
  - [x] Admin: `Faculty`/`Subject`/`Topic`/`Quiz` view'lari yangilandi
  - [x] `webapp.py` dan `/modules` route'lari olib tashlandi, `modules.html`, `module_quizzes.html` o'chirildi
  - [ ] ~~Alembic migratsiya~~ — T-111 da squash

### T-109 · `StudentProfile` modeli + `TelegramUser` bog'lanishi + migratsiya
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-108
- **Acceptance:**
  - [x] `app/models/student_profile.py` yaratildi (barcha maydonlar + CheckConstraint)
  - [x] `TelegramUser.profile` back-populates 1:1
  - [x] Admin view (`StudentProfileAdminView`) qo'shildi
  - [ ] ~~Alembic migratsiya~~ — T-111 da squash

### T-110 · `Attempt` ni `student_profile_id` ga o'tkazish + migratsiya
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-109
- **Acceptance:**
  - [x] `QuizAttempt.user_id` (telegram_users FK) → `student_profile_id` (student_profiles FK, CASCADE)
  - [x] Repository/service/handler yangilandi (yo'q — hali ishlatilmagan)
  - [ ] ~~Alembic migratsiya~~ — T-111 da squash

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
