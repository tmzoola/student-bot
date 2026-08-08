# Edu-bot — Vazifalar reestri

Yagona haqiqat manbai. ID lar ketma-ket, qayta ishlatilmaydi.
Statuslar: `todo`, `in_progress`, `done`, `blocked`.

---

## Loyiha holati (qisqacha)

Muslima Darmonova Edu Bot — Telegram Mini App + Admin Panel (aiogram 3 + FastAPI + Starlette-Admin + PostgreSQL). Asosiy modullar ishlab chiqarishga chiqarilgan: testlar (module → topic → quiz), reyting, kunlik test, konkurs (contest), do'kon + buyurtma FSM, admin panel (dark mode bilan). Oxirgi sprintlarda **kitoblar moduli** (PDF/EPUB yuklash, ichki o'qish), **dark mode** butun tizimda va **NSFW guard boti** (NudeNet lokal) qo'shilgan. `tests/` papkasi bo'sh — avtomatlashtirilgan test qoplami yo'q. Root'da `CLAUDE.md` mavjud emas.

**Stack:** aiogram 3.15, FastAPI 0.115, SQLAlchemy 2.x async, Alembic, starlette-admin 0.14, NudeNet 3.4, Docker Compose.

---

## Tugallangan ishlar

- [x] Bot: reply klaviatura, kunlik quiz push, re-engagement (3+ kun jim foydalanuvchi, 10:00 Tashkent)
- [x] Mini App: modullar → mavzular → testlar, timer, reyting (kun/hafta/oy/hammasi)
- [x] Kunlik test + sanoq (countdown)
- [x] Konkurs (contests) — jonli scoreboard, g'oliblar, Excel eksport
- [x] Do'kon kitoblari + buyurtma FSM (karta → tasdiq → yetkazish ma'lumotlari)
- [x] Admin panel: quiz builder, kontest builder, kitob yuklash, do'kon, buyurtmalar, reyting, motivatsiya, broadcast, foydalanuvchilar
- [x] Kitoblar moduli (PDF/EPUB, kategoriya, in-app o'qish)
- [x] Butun tizim bo'yicha dark/light mode
- [x] NSFW guard bot (NudeNet lokal, bio kalit so'zlari, threshold sozlamasi)
- [x] Foydalanuvchi ban, telefon raqami, `last_active_at` migratsiyalari

---

## Davom etayotgan / yarim qolgan ishlar

### T-001 · Kitoblar modulini yakunlash — reader UX
- **Owner:** frontend-developer
- **Status:** in_progress
- **Priority:** yuqori
- **Depends on:** —
- **Acceptance:**
  - [ ] `templates/books.html` da qidiruv va kategoriya filtri ishlaydi
  - [ ] PDF ichki reader oxirgi o'qilgan sahifani `localStorage` da saqlaydi
  - [ ] EPUB uchun font o'lchami/tungi rejim reader ichida ham qo'llaniladi
  - [ ] `downloads` hisoblagichi haqiqiy ochilishlarda oshadi (fake requestlarda emas)
- **Notes:** `app/templates/books.html` (154 qator), `models/book.py`.

### T-002 · NSFW guard — admin ko'rish oynasi
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** —
- **Acceptance:**
  - [ ] Admin panelda `guard` bo'limi: aniqlangan foydalanuvchilar ro'yxati, aniqlash sababi (rasm skori / bio kalit so'zi), qaror (kick/warn/ignore)
  - [ ] `models/guard.py` maydonlaridan foydalanadi
  - [ ] Threshold `.env` dan emas, admin UI orqali sozlanadi
- **Notes:** `services/nsfw_detector.py`, `guard/handlers.py`.

### T-003 · CLAUDE.md yozish
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** —
- **Acceptance:**
  - [ ] Root'da `CLAUDE.md` yaratildi
  - [ ] Stack, papka tuzilishi, kod uslubi (async SA session, models `str` import qoidasi), migratsiya buyruqlari, i18n (uz) konvensiyalari yozilgan
  - [ ] Kod yozayotgan agentlar uchun "qilma" ro'yxati (masalan: money as int UZS, Tashkent TZ)

---

## Keyingi vazifalar

### Yuqori prioritet

### T-004 · Avtomatlashtirilgan test skeleti
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** T-003
- **Acceptance:**
  - [ ] `pytest` + `pytest-asyncio` + `httpx` `requirements-dev.txt` ga qo'shildi
  - [ ] `tests/conftest.py` — async DB fixture (SQLite yoki test PG)
  - [ ] Kamida 3 ta smoke test: `/webapp/`, `/api/v1/leaderboard`, buyurtma yaratish
  - [ ] `make test` ishlaydi

### T-005 · Do'kon buyurtmalari — status kuzatuvi Mini App'da
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** —
- **Acceptance:**
  - [ ] `my_orders.html` da status timeline (yangi → to'landi → jo'natildi → yetkazildi)
  - [ ] Admin `admin_orders.html` da "jo'natildi" tugmasi mavjud bo'lishi (yo'q bo'lsa qo'shish)
  - [ ] Status o'zgarganda foydalanuvchi botga xabar oladi

### T-006 · Media fayllarni backup/retention
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** —
- **Acceptance:**
  - [ ] `docker-compose.yml` da `media` volume nomlangan (mavjud emas bo'lsa)
  - [ ] Kunlik `pg_dump` + `media/` arxivlash `entrypoint.sh` ga yoki alohida cron konteynerga qo'shilgan
  - [ ] `dump.sql` root'dan olib tashlanadi (repo'da 38KB dump yotibdi)

### O'rta prioritet

### T-007 · Broadcast — segmentatsiya
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** o'rta
- **Depends on:** —
- **Acceptance:**
  - [ ] "Xabar yuborish" admin sahifasida filter: faol (30 kun), ban qilingan, telefonli
  - [ ] Yuborishdan oldin qabul qiluvchilar soni ko'rsatiladi
  - [ ] Rate-limit (aiogram flood control) e'tiborga olinadi

### T-008 · Reyting keshi
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** o'rta
- **Depends on:** —
- **Acceptance:**
  - [ ] Kun/hafta/oy reytinglari 60 soniya keshda saqlanadi (in-memory yoki Redis)
  - [ ] Yangi urinish (attempt) tugagach kesh invalidatsiya qilinadi
  - [ ] `/api/v1/leaderboard` p95 kechikish o'lchandi

### T-009 · Web-designer — landing sahifa qayta ko'rib chiqish
- **Owner:** web-designer
- **Status:** todo
- **Priority:** o'rta
- **Depends on:** —
- **Acceptance:**
  - [ ] `public/index.html` va `public/admin.html` brend rangi, tipografiyasi bo'yicha audit
  - [ ] Mobile viewport'da CLS < 0.1
  - [ ] Dark mode ranglari WCAG AA kontrastda

### T-010 · Kontest — sovg'ani avtomatik yuborish flow
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** o'rta
- **Depends on:** —
- **Acceptance:**
  - [ ] Kontest tugagach top-N g'olibga bot avtomatik xabar yozadi
  - [ ] Admin panelda "sovg'a berildi" belgisi mavjud
  - [ ] Excel eksportda holat ustuni

### Past prioritet

### T-011 · i18n — ruscha til qo'shish
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** past

### T-012 · Foydalanuvchi profili — avatar
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** past

### T-013 · Motivatsion iqtiboslar — jadval bo'yicha
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** past

---

## Feature: Referral / Taklif linki (Malaka bot)

**Maqsad:** Malaka botni ko'p maqsadli qilish — foydalanuvchilar bot admin bo'lgan kanallar/guruhlarga o'zining shaxsiy taklif linkini olishadi, taklif qilingan a'zolar hisoblanadi va reyting/sovg'a asosini beradi.

**Nomlash tavsiyasi:** menyu tugmasi — `🔗 Taklif linki` (muqobil: `🎁 Do'stni taklif qil`, `👥 Referral`). Rasmiy variant: **`🔗 Taklif linki`**.

**MVP oralig'i:** T-014 → T-018 (kanal ro'yxati statik/`my_chat_member` orqali, invite link generatsiya, join tracking, foydalanuvchi ko'rinishi). T-019+ — reyting, sovg'a flow, xabarnomalar.

### T-014 · Referral — data modeli va migratsiya
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** —
- **Acceptance:**
  - [ ] `app/models/referral.py` yaratildi: `TrackedChat` (id, chat_id BIGINT unique, title, username, type[channel|group], is_active, added_at), `InviteLink` (id, user_id FK→telegram_user, chat_id FK→tracked_chat, invite_link str unique, tg_link_name, join_count int default 0, created_at, revoked_at nullable, UNIQUE(user_id, chat_id)), `InviteJoin` (id, invite_link_id FK, joined_user_tg_id BIGINT, joined_at, left_at nullable, is_counted bool)
  - [ ] `TelegramUser` ga back-populates aloqalari
  - [ ] Alembic migratsiya `make makemigrations msg="add_referral_tables"` orqali generatsiya qilindi va toza (indekslar: `invite_link.user_id`, `invite_join.invite_link_id`)
  - [ ] `app/models/__init__.py` da yangi modellar registratsiya qilingan
- **Notes:** Money/UZS integer konvensiyasiga rioya. Timezone `Asia/Tashkent`. `join_count` denormallashtirilgan hisoblagich — `InviteJoin` `is_counted=True` bo'yicha sinxronlashtiriladi.

### T-015 · Referral — kuzatiladigan chat ro'yxatini yig'ish (`my_chat_member`)
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** T-014
- **Acceptance:**
  - [ ] `app/bot/handlers/referral_admin_events.py` (yoki `router.py` ichida alohida router) — `my_chat_member` update'ini eshitadi
  - [ ] Bot chatga admin sifatida qo'shilganda `TrackedChat` upsert (`is_active=True`), demote/kick'da `is_active=False`
  - [ ] Faqat `can_invite_users` huquqi bor bo'lganda `is_active=True`; huquq yo'q bo'lsa `False` va sabab loglanadi
  - [ ] Bot handler'i `chat_member` update turini `allowed_updates` ga qo'shadi (`setup.py` da polling konfiguratsiyasi)
- **Notes:** Tavsiya — **avtomatik `my_chat_member` orqali**. Statik jadval qo'shimcha (admin panelda majburiy admin tomonidan yashirish/ko'rsatish tumblari). "Track Members" ruxsati kerakligini `TrackedChat.can_track_members` bool maydonida saqlash mumkin.

### T-016 · Referral — invite link generatsiya servisi
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** T-014, T-015
- **Acceptance:**
  - [ ] `app/services/referral.py`: `get_or_create_invite_link(session, user, chat_id) -> InviteLink`
  - [ ] Telegram `createChatInviteLink(chat_id, name=f"u{user.id}", creates_join_request=False)` chaqiriladi; `name` maydonida user ID
  - [ ] Mavjud (revoked_at IS NULL) link topilsa qayta ishlatiladi
  - [ ] Xatoliklar (`TelegramBadRequest`, bot admin emas va h.k.) `AppException` orqali graceful — foydalanuvchiga tushunarli xabar
  - [ ] Link `t.me/+HASH` shaklda qaytariladi
- **Notes:** Rate-limit — bir foydalanuvchi bir chat uchun bir link. Revoke UI keyingi bosqichda.

### T-017 · Referral — asosiy menyu tugmasi va bot handler'lari
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** T-016
- **Acceptance:**
  - [ ] `app/bot/router.py` `_main_keyboard()` ga yangi qator: `KeyboardButton(text="🔗 Taklif linki")` (mavjud 3 tugma bilan bir menyuda)
  - [ ] Bosilganda `TrackedChat.is_active=True` bo'lganlar inline keyboard bilan ko'rsatiladi (chat title + a'zolar soni ixtiyoriy)
  - [ ] Chat tanlangach servis (T-016) chaqirilib link qaytariladi: matn `🔗 Sizning shaxsiy linkingiz:\n{link}\n\nHozirgacha taklif qilinganlar: {count}`
  - [ ] Kanal ro'yxati bo'sh bo'lsa placeholder xabar
  - [ ] Xatolik holatlari uchun UX matnlari o'zbekcha
- **Notes:** Tugma matnini keyin `web-designer` bilan tekshirish mumkin.

### T-018 · Referral — a'zolarni track qilish (`chat_member`)
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** yuqori
- **Depends on:** T-016
- **Acceptance:**
  - [ ] `chat_member` update handler: `new_chat_member.status in {member, restricted}` va `old_chat_member.status in {left, kicked}` bo'lganda `update.invite_link.invite_link` bo'yicha `InviteLink` topib `InviteJoin` yozadi, `join_count` oshiradi (transaksion)
  - [ ] Xuddi shu foydalanuvchi chiqib qayta qo'shilsa dubl hisoblanmaydi (`UNIQUE(invite_link_id, joined_user_tg_id)`)
  - [ ] Chatdan chiqib ketganda `left_at` yoziladi (`is_counted=False` qilib denorm hisoblagichni kamaytirish — MVP'da ixtiyoriy, hujjatlashtirilsin)
  - [ ] `allowed_updates` ga `chat_member` qo'shilgan; bot uchun "Add Members / Invite Users" ruxsati kerakligi README/CLAUDE.md ga eslatma
- **Notes:** Anti-fraud (self-invite, bot accountlar) — keyingi vazifa.

### T-019 · Referral — admin panel view'lari (starlette-admin)
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** o'rta
- **Depends on:** T-014, T-018
- **Acceptance:**
  - [ ] `app/admin/views/referral.py`: `TrackedChatView`, `InviteLinkView`, `InviteJoinView` (i18n uz label'lar)
  - [ ] `InviteLinkView` da `user`, `chat`, `join_count`, `created_at` ustunlari, `user_id`/`chat_id` bo'yicha filter
  - [ ] `TrackedChat` uchun `is_active` inline tahrir
  - [ ] Admin registratsiyasi `app/admin/__init__.py` da
- **Notes:** Dark mode uslubiga mos bo'lishi kerak.

### T-020 · Referral — reyting sahifasi (top inviters)
- **Owner:** frontend-developer
- **Status:** todo
- **Priority:** o'rta
- **Depends on:** T-019
- **Acceptance:**
  - [ ] Admin panelda `/admin/referral-leaderboard` sahifasi — foydalanuvchi, jami taklif, chatlar bo'yicha breakdown
  - [ ] Chat filtri (bitta / hammasi) va davr filtri (hamma vaqt / joriy oy)
  - [ ] Excel eksport (kontest eksport patterni bilan bir uslubda)
- **Notes:** Keshlash — T-008 patterniga o'xshash.

### T-021 · Referral — sovg'a (reward) tizimi asosini qo'yish
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** o'rta
- **Depends on:** T-020
- **Acceptance:**
  - [ ] `ReferralReward` modeli (threshold_count int, title, description, is_active), `UserRewardClaim` (user_id, reward_id, granted_at, delivered_at nullable)
  - [ ] Foydalanuvchi thresholdga yetganda bot avtomatik tabrik yuboradi va adminga `GUARD_ADMIN_CHAT_ID` (yoki alohida `REFERRAL_ADMIN_CHAT_ID`) ga bildirishnoma
  - [ ] Admin panelda claim'lar ro'yxati va "yetkazildi" tugmasi
- **Notes:** Mukofot yetkazish flow — kontest sovg'a flow (T-010) bilan birlashtirish mumkinligi tekshirilsin.

### T-022 · Referral — anti-fraud va cheklovlar
- **Owner:** solutions-architect
- **Status:** todo
- **Priority:** past
- **Depends on:** T-018
- **Acceptance:**
  - [ ] O'zi o'zini taklif qilish bloklanadi
  - [ ] Bir joined_user_tg_id turli linklar bo'yicha faqat 1 marta hisoblanadi (global unique)
  - [ ] Chiqib qayta qo'shilish cooldown (masalan 30 kun) yoki umuman qayta hisoblanmaydi
  - [ ] Admin panelda "shubhali" belgisi

---

## Texnik qarz va yaxshilashlar

- [ ] `dump.sql` (38KB) va `.env` fayllari repo'da — `.env` `.gitignore`da bo'lishiga qaramay `.env.example` bilan sinxronlashtirish kerak; `dump.sql` olib tashlansin
- [ ] `tests/` bo'sh — CI yo'q
- [ ] `app/collect_static.py` — vazifasi va integratsiyasi hujjatlashtirilmagan
- [ ] `admin_img/`, `webview_img/`, `public/` — statik fayllar joyi noaniq, konvensiya kerak
- [ ] `services/notifications.py` scheduler asyncio loop'ida — konteyner qayta ishga tushganda missed run qayd qilinmaydi
- [ ] Pul (UZS) integer'da saqlanishi kod izohlarida bor, lekin schema level check yo'q (`CheckConstraint >= 0`)
- [ ] `NudeDetector` og'ir — guard bot alohida konteynerga ajratilishi mumkin
- [ ] Alembic versiya IDlari qo'lda yozilgan (`g4d1e95...`) — konvensiya rasmiy emas
- [ ] Type hints qisman (`repositories/`, `uow/` audit kerak)
- [ ] Pre-commit (ruff/black) sozlanmagan

---

**Boshlash uchun bitta vazifa:** T-014 — `solutions-architect` ni chaqiring (Referral data modeli va migratsiya). T-003 (CLAUDE.md) allaqachon root'da mavjud — statusi yopilishi kerak.
