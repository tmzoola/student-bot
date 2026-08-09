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
- **Status:** done
- **Depends on:** T-205
- **Acceptance:**
  - [x] `GET /subjects/{id}` HTML — mavzular + har birida testlar
  - [x] `GET /api/v1/subjects/{id}` JSON
  - [x] Foydalanuvchi profili fan bilan mos kelishi (403 aks holda)
  - [x] Template `subject_detail.html`

### T-207 · Test yechish
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-206
- **Acceptance:**
  - [x] `GET /quiz/{id}` HTML (`quiz.html` qayta ishlatildi)
  - [x] `GET /api/v1/quiz/{id}` JSON (correct_option qaytmaydi)
  - [x] `POST /api/v1/quiz/{id}/submit` — QuizAttempt yaratiladi, score hisoblanadi
  - [x] Fan foydalanuvchi profiliga mosligi tekshiriladi

### T-208 · Profil sahifasi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-207
- **Acceptance:**
  - [x] `GET /profile` HTML
  - [x] `GET /api/v1/profile` JSON (profil + statistika)
  - [x] `GET /api/v1/profile/attempts` JSON (so'nggi 20)
  - [x] Template'da urinishlar tarixi

### T-209 · Smoke testlar
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-208
- **Acceptance:**
  - [x] `requirements-dev.txt` yaratildi
  - [x] `tests/conftest.py` (async SQLite fixture)
  - [x] `tests/test_registration.py`
  - [x] `tests/test_quiz_submit.py`
  - [x] `Makefile` da `test:` target
  - [x] `pytest -q` yashil (4 passed)

## Bosqich 3 — AI taxlil

Talaba urinishlari asosida kuchli/zaif tomonlarni aniqlash, mavzular bo'yicha
tavsiyalar. Bosqich 5 tugagach boshlangan. Manba: `QuizAttempt` (kanonik) +
`GeneratedQuizAttempt` (AI Material). AI provider: Claude Sonnet 4.6 (tool use).
Kesh: Redis `insight:<profile_id>` TTL 24 soat. Min urinish: 3.

### T-301 · Statistika servisi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-510
- **Acceptance:**
  - [x] `app/services/insights/stats.py` — `compute_user_stats(db, profile_id)`
  - [x] `UserStats` dataclass: `attempts_total`, `overall_accuracy_pct`, `by_topic`, `by_subject`, `recent_trend` (4 hafta), `top_weaknesses`, `top_strengths`
  - [x] `TopicStat` (subject_name bilan), `SubjectStat`, `TrendPoint`
  - [x] Kanonik va AI attempts birlashtiriladi (AI = "AI materiallar" virtual subject)
  - [x] `by_topic` faqat >=2 urinishga ega mavzular
  - [x] `tests/test_insights_stats.py` — 3 test (happy, single-attempt skip, empty)

### T-302 · WebApp /insights sahifasi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-301
- **Acceptance:**
  - [x] `GET /insights` HTML → `templates/insights.html`
  - [x] `GET /api/v1/insights` JSON — stats + (agar kesh bor bo'lsa) `ai_insight`
  - [x] Statistika kartochkalar, zaif/kuchli mavzular ro'yxati, SVG trend line
  - [x] "AI tavsiya olish" tugma (yoki "Qayta so'rash")
  - [x] `attempts_total < 3` → "Yetarli ma'lumot yo'q" empty state

### T-303 · AI insight generatsiya servisi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-301
- **Acceptance:**
  - [x] `app/services/insights/ai_analyze.py` — `generate_insight(stats, profile)`
  - [x] `InsightResult` dataclass: `summary`, `weaknesses[{topic, tip, accuracy}]`, `strengths[{topic, accuracy}]`, `recommendations[str]`, `input_tokens`, `output_tokens`
  - [x] Claude tool use (`submit_insight` schema) + prompt caching
  - [x] O'zbek tili (system prompt), amaliy va o'lchovli tavsiyalar
  - [x] `ai_call_cost kind=insight` structured log
  - [x] `tests/test_insights_ai.py` — 4 test (happy mock, no tool_use, empty key, dict roundtrip)

### T-304 · Bot menyuga "🧠 Tahlilim" tugma
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-302
- **Acceptance:**
  - [x] `bot/handlers/menu.py` `_inline_webapp_kb()` ga uchinchi qator qo'shildi
  - [x] URL: `WEBAPP_URL/insights`

### T-305 · Redis kesh + rate limit integratsiyasi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-303
- **Acceptance:**
  - [x] `app/services/insights/cache.py` — `get/set/invalidate_cached_insight`, TTL 24h
  - [x] `POST /api/v1/insights/generate` — kesh bor bo'lsa qaytar (rate limit sarflanmaydi), yo'q bo'lsa `check_and_increment_daily` + `generate_insight` + `set_cached_insight`
  - [x] `GET /api/v1/insights` — faqat keshdagi insight qaytaradi (avtomatik AI chaqirmaydi)
  - [x] `<3` urinish → 400 "Yetarli ma'lumot yo'q"
  - [x] `tests/test_insights_cache.py` — 3 test (no Redis miss, set/get, invalidate)

### T-306 · Admin panelda talaba tahlili sahifasi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-305
- **Acceptance:**
  - [x] `GET /admin-tools/insight/<profile_id>` — Jinja render
  - [x] `templates/admin_insight.html` — statistika + kesh AI insight
  - [x] Read-only; AI shu yerdan chaqirilmaydi (faqat keshdan)

### T-307 · Testlar
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-306
- **Acceptance:**
  - [x] `tests/test_insights_stats.py` (T-301 da)
  - [x] `tests/test_insights_ai.py` (T-303 da)
  - [x] `tests/test_insights_cache.py` (T-305 da)
  - [x] `pytest -q` yashil (34 passed)

---

## Bosqich 5 — Material yuklash + AI test generatsiya (MVP)

**Maqsad:** Talaba PDF/DOCX/TXT material yuklaydi → server matnni ajratadi → Claude API 10 ta MCQ savol yaratadi → talaba WebApp'da yechadi. Bu Anki + ChatGPT tutor'ning boshlanishi.

**Domen strategiyasi:** Admin-created `Faculty/Subject/Topic/Quiz` **saqlanadi** (kanonik test bankasi). Yangi `Material → GeneratedQuiz → GeneratedQuestion` **yonida** joylashadi. Talaba ikkisidan ham foydalanadi.

**AI:** Anthropic Claude birinchi. `AI_PROVIDER=claude`, `ANTHROPIC_API_KEY=...`. Provider abstraksiyasi keyingi providerlar (OpenAI) uchun tayyor bo'lsin.

**Scope v1:** faqat MCQ (4 variantli). True/false, ochiq savol keyingi versiyaga.

### T-501 · Material domen modellari + migratsiya
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-407
- **Acceptance:**
  - [x] `app/models/material.py`: `Material(id, student_profile_id FK, title, filename, mime, size_bytes, storage_path, status ENUM(uploaded|extracting|generating|ready|failed), extracted_text_length, error_message, created_at, updated_at)`
  - [x] `app/models/material_chunk.py`: `MaterialChunk(id, material_id FK CASCADE, order int, text)`
  - [x] `app/models/generated_quiz.py`: `GeneratedQuiz(id, material_id FK CASCADE, student_profile_id FK, title, difficulty ENUM(easy|medium|hard), language, num_questions, created_at)`
  - [x] `app/models/generated_question.py`: `GeneratedQuestion(id, generated_quiz_id FK CASCADE, order, text, option_a..d, correct_option (correct_option_enum), explanation)`
  - [x] `app/models/generated_attempt.py`: `GeneratedQuizAttempt(id, generated_quiz_id FK, student_profile_id FK, score, total, answers JSON, time_taken_seconds, completed_at)`
  - [x] `models/__init__.py` yangilangan
  - [x] Alembic migratsiya `0002_bosqich_5.py` — Postgres 15 da upgrade/downgrade xatosiz

### T-502 · File upload + text extraction
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-501
- **Acceptance:**
  - [x] `requirements.txt` ga `pymupdf`, `python-docx` qo'shildi
  - [x] `app/services/materials/extract.py`: `extract_text(path, mime) -> str` — PDF/DOCX/TXT
  - [x] `app/services/materials/chunk.py`: `chunk_text(text, max_chars=2000)` paragraf chegarasida
  - [x] `MAX_MATERIAL_SIZE = 20 MB`, `ALLOWED_MIMES` (PDF/DOCX/TXT)
  - [x] `tests/test_extraction.py` — 7 test yashil (PDF/DOCX/TXT + chunk)
  - [ ] Fayllar `MEDIA_ROOT/materials/<profile_id>/<uuid>.<ext>` — T-506 upload endpoint'da

### T-503 · AI service — Claude provider
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-502
- **Acceptance:**
  - [x] `requirements.txt` ga `anthropic==0.42.0` qo'shildi
  - [x] `services/ai/base.py` — `AIProvider` ABC + `AIProviderError`
  - [x] `services/ai/schemas.py` — `QuizGenResult`, `GeneratedQuestionData`
  - [x] `services/ai/claude.py` — `ClaudeProvider` (AsyncAnthropic + tool use + prompt caching)
  - [x] `services/ai/__init__.py` — `get_ai_provider()` factory
  - [x] `settings.AI_PROVIDER`, `AI_MODEL`, `ANTHROPIC_API_KEY`, `AI_DAILY_LIMIT_PER_USER`, `MAX_MATERIAL_SIZE`
  - [x] `.env.example` yangilandi
  - [x] `services/ai/prompts.py` — o'zbek/rus/ingliz til, difficulty hint, `submit_quiz` tool schema

### T-504 · Test generatsiya servisi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-503
- **Acceptance:**
  - [x] `app/services/materials/generate.py`: `async generate_quiz_for_material(material_id, num_questions=10, difficulty="medium") -> GeneratedQuiz`
  - [x] Material chunk'larni jamlab context sifatida beradi (juda uzun bo'lsa oxirgi ~200_000 char'gacha qisqartiradi)
  - [x] AI natijasini DB'ga yozadi (`GeneratedQuiz` + `GeneratedQuestion` batch insert, bir tranzaksiya)
  - [x] Xato holida `material.status = failed`, `error_message` yoziladi, log qilinadi
  - [x] Retry: bir marta qayta urinish (2s sleep, `AIProviderError` uchun)
  - [x] Test: AI response mock qilinib 3 stsenariy tekshirildi

### T-505 · Bot flow — material yuklash trigger
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-504
- **Acceptance:**
  - [x] Menyuga inline "📄 Material yuklash" tugmasi qo'shildi (WebApp'ga `/materials`)
  - [x] Bot chatda `Message.document` ni qabul qiladi — fayl `MEDIA_ROOT/materials/<profile_id>/<uuid>.<ext>` ga saqlanadi, `Material(status=uploaded)` yaratiladi, background task ishga tushadi
  - [x] Progress: "📥 Yuklandi → 🔎 Matn ajratildi → 🤖 Test yaratilmoqda → ✅ Tayyor" xabar edit
  - [x] Tayyor bo'lgach inline "🧠 Testni ochish" tugma (WebApp `/materials/{id}/quiz/{quiz_id}`)
  - [x] Xatolik holida foydalanuvchiga tushunarli xabar (mime, hajm, extract, AI)

### T-506 · WebApp `/materials` sahifasi
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-505
- **Acceptance:**
  - [x] `GET /materials` HTML — upload input + kartochka'lar (5 sek polling)
  - [x] `POST /api/v1/materials/upload` — multipart, streaming write, 20 MB limit, `_process_material_no_chat` background task
  - [x] `GET /api/v1/materials` — JSON (id, title, status, size, quizzes_count, error_message, created_at)
  - [x] `GET /api/v1/materials/{id}` — JSON detail + generated_quizzes
  - [x] Template `materials.html` (drag & drop, polling)

### T-507 · WebApp — generated quiz yechish
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-506
- **Acceptance:**
  - [x] `GET /materials/{material_id}/quiz/{quiz_id}` HTML — yangi `generated_quiz.html` (quiz.html pattern reuse)
  - [x] `GET /api/v1/generated-quiz/{id}` — savollar (correct_option YASHIRIN)
  - [x] `POST /api/v1/generated-quiz/{id}/submit` — `GeneratedQuizAttempt` + score + tushuntirishlar bilan JSON
  - [x] `student_profile_id` mosligi 403 bilan tekshiriladi

### T-508 · Admin panelda audit view'lari
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-507
- **Acceptance:**
  - [x] `MaterialAdminView` — talaba, hajm, status, xato sabab
  - [x] `GeneratedQuizAdminView` + `GeneratedQuestionAdminView` — sarlavha, qiyinlik, savol matni, to'g'ri variant
  - [x] "AI Materiallar" DropDown qo'shildi

### T-509 · Rate limiting + cost logging
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-508
- **Acceptance:**
  - [x] `settings.AI_DAILY_LIMIT_PER_USER = 20` (default `.env.example`)
  - [x] `services/ai_rate_limit.py` — Redis pipeline `INCR + EXPIRE 24h`
  - [x] Limit oshsa `HTTPException(429)`; Redis mavjud bo'lmasa log warn + bypass
  - [x] `services/ai/claude.py` da `ai_call_cost provider=... input_tokens=... output_tokens=...` structured log
  - [x] `tests/test_rate_limit.py` — 3 test (under limit, over limit 429, no redis bypass)

### T-510 · Bosqich 5 testlari
- **Owner:** solutions-architect
- **Status:** done
- **Depends on:** T-509
- **Acceptance:**
  - [x] `tests/test_extraction.py` — PDF, DOCX, TXT extract (T-502 da tayyor)
  - [x] `tests/test_ai_provider.py` — Claude provider mock (4 test: valid parse, no tool_use, invalid schema, empty key)
  - [x] `tests/test_generate_quiz.py` — end-to-end mock (T-504 da 3 test)
  - [x] `tests/test_generated_submit.py` — score, correct_option yashirilishi, begona profil 403
  - [x] `pytest -q` yashil (24 passed)

## Bosqich 4 — Deploy va CI/CD

Server: **13.140.165.210** (Contabo VPS, Ubuntu). Tashqi port **8002**
(edu-bot 8001, samandar_market 8000 bilan konflikt yo'q). Domen —
**student-13-140-165-210.sslip.io** (sslip.io orqali IP'ga avtomatik).

Har vazifa bitta commit bilan yakunlanadi.

### T-401 · Dockerfile va entrypoint tozalash
- **Owner:** devops
- **Status:** done
- **Depends on:** T-209
- **Acceptance:**
  - [x] `Dockerfile` dan NudeNet RUN satri olib tashlandi
  - [x] `app/collect_static.py` olib tashlandi (placeholder edi) va `entrypoint.sh` dan chaqiruv chiqarildi
  - [x] `apt` kesh tozalanadi (`apt-get clean && rm -rf /var/lib/apt/lists/*`)
  - [x] `requirements.txt` da nudenet/onnxruntime yo'qligi tasdiqlandi
  - [x] `docker compose config` xatosiz

### T-402 · docker-compose port va domain sozlash
- **Owner:** devops
- **Status:** done
- **Depends on:** T-401
- **Acceptance:**
  - [x] `app` porti `8000:8000` → `8002:8000`
  - [x] Grafana `GF_SERVER_ROOT_URL` → `https://student-13-140-165-210.sslip.io/grafana`
  - [x] Barcha container_name'lar `student_*` prefiks bilan (audit tasdiqladi)
  - [x] `depends_on` va `healthcheck` audit qilindi
  - [x] Dozzle healthcheck `/dozzle healthcheck` ga o'zgartirildi (distroless image)
  - [x] Dozzle/Grafana host loopback binding qo'shildi (nginx uchun)
  - [x] `docker compose config` xatosiz

### T-403 · `.env.example` ni deploy uchun to'liq yangilash
- **Owner:** devops
- **Status:** done
- **Depends on:** T-402
- **Acceptance:**
  - [x] Barcha kerakli o'zgaruvchilar guruhlangan (App, DB, Admin, Bot, WebApp, Redis, Grafana, AI, University)
  - [x] `WEBAPP_URL=https://student-13-140-165-210.sslip.io`
  - [x] Har guruh uchun izoh (o'zbek)
  - [x] Deploy uchun majburiy o'zgaruvchilar `# REQUIRED` bilan belgilangan

### T-404 · Nginx reverse proxy config
- **Owner:** devops
- **Status:** done
- **Depends on:** T-403
- **Acceptance:**
  - [x] `deploy/nginx/student-bot.conf` yaratildi
  - [x] HTTP → HTTPS 301 redirect (Let's Encrypt challenge path saqlangan)
  - [x] `/` → `127.0.0.1:8002` (app)
  - [x] `/logs/` → Dozzle (basic auth), `/grafana/` → Grafana (subpath, slashsiz proxy_pass)
  - [x] X-Forwarded-* header'lar, WebSocket upgrade map
  - [x] `client_max_body_size 100M`
  - [x] Certbot komandasi + htpasswd komandasi izohda

### T-405 · GitHub Actions deploy audit
- **Owner:** devops
- **Status:** done
- **Depends on:** T-404
- **Acceptance:**
  - [x] `.github/workflows/deploy.yml` student-bot uchun moslashtirildi (path secret orqali)
  - [x] Talab qilinadigan secretslar ro'yxati DEPLOY_NOTES.md ga yozildi (T-406)
  - [x] Trigger: `push` to `main` + `workflow_dispatch`, concurrency guard
  - [x] SSH orqali `git pull && docker compose up -d --build` + post-deploy log grep

### T-406 · `docs/DEPLOY_NOTES.md` qayta yozish
- **Owner:** devops
- **Status:** done
- **Depends on:** T-405
- **Acceptance:**
  - [x] Server sozlash, klonlash, `.env`, dastlabki up, Nginx+TLS, Actions, backup, monitoring, yangilash, rollback bo'limlari
  - [x] Barcha domain/IP student-bot uchun (`13.140.165.210`, `student-13-140-165-210.sslip.io`)

### T-407 · Kunlik backup skripti
- **Owner:** devops
- **Status:** done
- **Depends on:** T-406
- **Acceptance:**
  - [x] `deploy/scripts/backup.sh` — pg_dump + media tar.gz
  - [x] 7 kunlik retention (`find -mtime +7 -delete`)
  - [x] Cron qatori DEPLOY_NOTES.md 6-bo'limda hujjatlashtirilgan
  - [x] Idempotent (`.tmp` orqali atomik yozish)
  - [x] `bash -n` sintaksis check o'tdi

---

## Texnik qarz (kuzatib boriladigan)

- [ ] `tests/` bo'sh — CI yo'q
- [ ] `dump.sql` mavjud bo'lsa repo'dan olib tashlansin
- [ ] Pre-commit (ruff/black) sozlanmagan
- [ ] Type hints qisman (`repositories/`, `uow/` audit kerak)

---

**Joriy fokus:** Bosqich 1 (T-101…T-111) tugatildi. Keyingi bosqich — Bosqich 2 (bot auth va student flow).
