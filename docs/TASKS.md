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
- **Status:** done
- **Depends on:** T-110
- **Acceptance:**
  - [x] `app/migrations/versions/` tozalandi (22 eski migratsiya o'chirildi)
  - [x] Yangi `0001_initial.py` autogenerate qilindi — faculties, subjects, topics, quizzes, questions, quiz_attempts, telegram_users, student_profiles
  - [x] Bo'sh Postgres 15 da `alembic upgrade head` xatosiz o'tdi
  - [x] `alembic downgrade base` ham xatosiz

---

## Bosqich 2 — Bot auth va student flow

Har bir vazifa bitta commit. Tartib qat'iy.

### T-201 · Ro'yxatdan o'tish FSM
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-111
- **Acceptance:**
  - [x] `app/bot/handlers/registration.py` yaratildi (FSM `waiting_student_id → waiting_full_name → waiting_faculty → waiting_course → waiting_semester`)
  - [x] `/start`: `StudentProfile` mavjud bo'lmasa FSM boshlanadi
  - [x] Fakultet DB'dan (`Faculty.is_active=True`) inline keyboard
  - [x] Kurs 1..4, semestr 1..2 inline
  - [x] Tugagach `StudentProfile(is_approved=False)` yaratiladi
  - [x] `bot/setup.py` da router include qilindi
  - [x] `ADMIN_CHAT_ID` config va `.env.example` ga qo'shildi

### T-202 · Admin approve/reject flow
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-201
- **Acceptance:**
  - [x] `app/bot/handlers/admin_approval.py` yaratildi
  - [x] T-201 tugagach `ADMIN_CHAT_ID` ga profil ma'lumotlari va tugmalar bilan xabar
  - [x] Approve: `is_approved=True`, `approved_at`, `approved_by`; foydalanuvchi xabar oladi va menyu ko'radi
  - [x] Reject: profil o'chiriladi; foydalanuvchi rad xabari oladi
  - [x] Faqat `ADMIN_CHAT_ID` dan kelgan callback'lar qabul qilinadi
  - [x] `ADMIN_CHAT_ID=0` bo'lsa notify o'tkazib yuboriladi (log warn)

### T-203 · Asosiy menyu
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-202
- **Acceptance:**
  - [x] `app/bot/handlers/menu.py` yaratildi
  - [x] Tasdiqlangan foydalanuvchi uchun reply keyboard `[📚 Fanlar (WebApp)] [👤 Profil] [📊 Statistika]`
  - [x] `📚 Fanlar` — WebApp tugmasi (`web_app=WebAppInfo(url=WEBAPP_URL+'/subjects')`)
  - [x] `👤 Profil` — F.I.Sh, ID, fakultet, kurs, semestr
  - [x] `📊 Statistika` — urinishlar soni, umumiy ball, o'rtacha foiz
  - [x] Tasdiqlanmagan/ro'yxatdan o'tmagan foydalanuvchilarga menyu ko'rinmaydi

### T-204 · Reg-gate middleware
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-203
- **Acceptance:**
  - [x] `RegistrationGateMiddleware` `bot/middlewares.py` ga qo'shildi
  - [x] `StudentProfile` yo'q → faqat `/start` va FSM update'lari o'tadi
  - [x] `is_approved=False` → faqat `/start` o'tadi
  - [x] `setup.py` da middleware register qilindi

### T-205 · WebApp /subjects endpoint + sahifa
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-204
- **Acceptance:**
  - [x] `GET /subjects` HTML — foydalanuvchi profiliga mos fanlar
  - [x] `GET /api/v1/subjects` JSON
  - [x] WebApp initData HMAC-SHA256 validation (`app/utils/webapp_auth.py`)
  - [x] Template `subjects.html`
  - [x] Profil topilmasa/tasdiqlanmasa 403

### T-206 · WebApp fan detail (mavzular va testlar)
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-205
- **Acceptance:**
  - [ ] `GET /subjects/{id}` HTML — mavzular + har birida testlar
  - [ ] `GET /api/v1/subjects/{id}` JSON
  - [ ] Foydalanuvchi profili fan bilan mos kelishi (403 aks holda)
  - [ ] Template `subject_detail.html`

### T-207 · Test yechish
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-206
- **Acceptance:**
  - [ ] `GET /quiz/{id}` HTML (`quiz.html` qayta ishlatildi)
  - [ ] `GET /api/v1/quiz/{id}` JSON (correct_option qaytmaydi)
  - [ ] `POST /api/v1/quiz/{id}/submit` — QuizAttempt yaratiladi, score hisoblanadi
  - [ ] Fan foydalanuvchi profiliga mosligi tekshiriladi

### T-208 · Profil sahifasi
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-207
- **Acceptance:**
  - [ ] `GET /profile` HTML
  - [ ] `GET /api/v1/profile` JSON (profil + statistika)
  - [ ] `GET /api/v1/profile/attempts` JSON (so'nggi 20)
  - [ ] Template'da urinishlar tarixi

### T-209 · Smoke testlar
- **Owner:** solutions-architect
- **Status:** todo
- **Depends on:** T-208
- **Acceptance:**
  - [ ] `requirements-dev.txt` yaratildi
  - [ ] `tests/conftest.py` (async SQLite fixture)
  - [ ] `tests/test_registration.py`
  - [ ] `tests/test_quiz_submit.py`
  - [ ] `Makefile` da `test:` target
  - [ ] `pytest -q` yashil

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

**Joriy fokus:** Bosqich 1 (T-101…T-111) tugatildi. Keyingi bosqich — Bosqich 2 (bot auth va student flow).
