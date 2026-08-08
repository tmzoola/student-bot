# Student-bot — Deploy va monitoring qo'llanmasi

Server: **13.140.165.210** (Contabo VPS, Ubuntu)
Domen: **student-13-140-165-210.sslip.io** (sslip.io IP'ga avtomatik ishora qiladi — DNS sozlash shart emas)
Tashqi port: **8002** (edu-bot 8001, samandar_market 8000 bilan konflikt yo'q)
Loyiha yo'li: `/opt/student-bot` (tavsiya)

Ushbu hujjatning tartibi — birinchi marta serverni ko'targaningizda yuqoridan
pastga bajaring. Keyingi safar faqat "8. Yangilanish" va zarur bo'lsa "9.
Rollback" bo'limlari kerak bo'ladi.

---

## 1. Server tayyorlash (bir marta)

### 1.1. Asosiy paketlar

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    docker.io docker-compose-plugin \
    nginx certbot python3-certbot-nginx \
    apache2-utils git curl ufw
sudo systemctl enable --now docker nginx
sudo usermod -aG docker "$USER"   # sessiya qayta boshlansin
```

> Compose komandasi: `docker compose ...` (plugin, v2). Agar serverda faqat
> `docker-compose` (v1) o'rnatilgan bo'lsa — barcha buyruqlarda `docker
> compose` ni `docker-compose` bilan almashtiring.

### 1.2. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'    # 80, 443
sudo ufw enable
```

**8002-portni tashqariga ochmang** — u faqat nginx orqali kirilishi kerak.

### 1.3. Deploy foydalanuvchi + SSH kaliti

```bash
# GitHub Actions uchun deploy foydalanuvchisi (yoki mavjudni qo'llang).
sudo adduser --disabled-password --gecos '' deploy
sudo usermod -aG docker deploy

# Lokal mashinada:  ssh-keygen -t ed25519 -f ~/.ssh/student-bot-deploy
# Public key'ni serverga qo'shing:
sudo -u deploy mkdir -p /home/deploy/.ssh
echo "<lokal public key>" | sudo -u deploy tee -a /home/deploy/.ssh/authorized_keys
sudo -u deploy chmod 600 /home/deploy/.ssh/authorized_keys
```

Private key GitHub secrets `SSH_KEY` ga yoziladi (5.1-bo'lim).

---

## 2. Loyihani klon qilish va `.env` to'ldirish

```bash
sudo mkdir -p /opt/student-bot
sudo chown deploy:deploy /opt/student-bot
sudo -u deploy git clone https://github.com/<org>/student-bot.git /opt/student-bot
cd /opt/student-bot
sudo -u deploy cp .env.example .env
sudo -u deploy nano .env
```

Majburiy o'zgaruvchilar (`.env.example` da `# REQUIRED` bilan belgilangan):

- `SECRET_KEY` — `openssl rand -hex 32`
- `POSTGRES_USER`, `POSTGRES_PASSWORD` — kuchli parol
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` — admin panel uchun
- `BOT_TOKEN`, `BOT_USERNAME` — @BotFather'dan
- `WEBAPP_URL=https://student-13-140-165-210.sslip.io`
- `ADMIN_CHAT_ID` — talaba arizasi keladigan chat (@userinfobot)
- `GRAFANA_ADMIN_PASSWORD` — kuchli parol

**Diqqat:** `.env` ni hech qachon git'ga commit qilmang. `.env` fayli
faqat serverda tahrirlanadi.

---

## 3. Dastlabki `docker compose up`

```bash
cd /opt/student-bot
sudo -u deploy docker compose up -d --build
sudo -u deploy docker compose ps
```

Kutilgan xizmatlar (barchasi `healthy` yoki `running`):

```
student_db, student_redis, student_app, student_bot,
student_dozzle, student_loki, student_promtail, student_grafana
```

Migratsiya avtomatik ishlaydi (`entrypoint.sh` ichida `alembic upgrade head`).
Qo'lda qilish kerak emas.

Health smoke:

```bash
curl -sf http://127.0.0.1:8002/health && echo OK
docker compose logs --since 60s app bot | grep -iE 'error|traceback' || echo "log toza"
```

---

## 4. Nginx + TLS

```bash
# Config'ni joyiga qo'ying va yoqing
sudo cp /opt/student-bot/deploy/nginx/student-bot.conf \
        /etc/nginx/sites-available/student-bot.conf
sudo ln -sf /etc/nginx/sites-available/student-bot.conf \
            /etc/nginx/sites-enabled/student-bot.conf
sudo nginx -t && sudo systemctl reload nginx

# Dozzle uchun basic auth
sudo htpasswd -c /etc/nginx/.htpasswd_student_logs admin

# TLS sertifikat (Let's Encrypt, avtomatik yangilanadi)
sudo certbot --nginx -d student-13-140-165-210.sslip.io
```

Certbot config faylni tahrirlab `ssl_certificate` yo'llarini yozadi.

Tekshirish:

```bash
curl -I https://student-13-140-165-210.sslip.io/health
# HTTP/2 200
```

---

## 5. GitHub Actions (avtomatik deploy)

### 5.1. Talab qilinadigan secretslar

Repo → Settings → Secrets and variables → Actions → **New repository secret**:

| Secret | Qiymat namunasi |
|--------|-----------------|
| `SSH_HOST` | `13.140.165.210` |
| `SSH_USER` | `deploy` |
| `SSH_KEY` | Private ed25519 kalit (butun matn `-----BEGIN...-----END-----`) |
| `DEPLOY_PATH` | `/opt/student-bot` |

### 5.2. Deploy trigger

- `main` branch'iga har `push` — avtomatik deploy.
- Qo'lda: Actions → **Deploy student-bot to Contabo** → **Run workflow**.

Workflow SSH orqali serverga kiradi, `git reset --hard origin/main` qiladi,
`docker compose up -d --build --remove-orphans` ishga tushiradi, oxirida 60
soniyalik log'ni xatolarga tekshiradi.

---

## 6. Kunlik backup

`deploy/scripts/backup.sh` — Postgres dump + media volume tar. 7 kunlik retention.

O'rnatish:

```bash
sudo mkdir -p /var/backups/student-bot
sudo chown deploy:deploy /var/backups/student-bot

# Cron (deploy foydalanuvchisi ostida):
sudo -u deploy crontab -e
# Qo'shing:
0 3 * * * /opt/student-bot/deploy/scripts/backup.sh >> /var/log/student-bot-backup.log 2>&1
```

Test:

```bash
sudo -u deploy /opt/student-bot/deploy/scripts/backup.sh
ls -lh /var/backups/student-bot/
```

Batafsil — `deploy/scripts/backup.sh` ichidagi izohlar.

---

## 7. Monitoring

| URL | Nima |
|-----|------|
| `https://student-13-140-165-210.sslip.io/logs/` | Dozzle — real-vaqt log (basic auth) |
| `https://student-13-140-165-210.sslip.io/grafana/` | Grafana — dashboard + tarix + alert |

Grafana birinchi kirishdan keyin:

1. Login: `admin` / `.env` dagi `GRAFANA_ADMIN_PASSWORD`.
2. **Explore** → Loki → `{container="student_app"}` — log oqim ko'rinishi kerak.
3. **Dashboards** → **New** → **Import** → `13639` (Loki Metrics) yoki `15140`
   (Docker Container Logs).
4. **Alerting** — Telegram notification channel (bot token + chat_id) qo'shing.

**Grafana parol volume mavjud bo'lsa `.env` dan qayta o'qilmaydi.** Almashtirish:

```bash
docker exec student_grafana grafana cli \
    --homepath /usr/share/grafana admin reset-admin-password '<yangi>'
```

Foydali `make` targetlari (agar lokal Makefile bilan bir xil bo'lsa):

```bash
make health          # /health
make logs-errors     # xatolar
make db-connections  # Postgres active
```

---

## 8. Yangilanish flow

Standart: `git push origin main` → GitHub Actions o'zi deploy qiladi.

Qo'lda deploy kerak bo'lsa:

```bash
cd /opt/student-bot
sudo -u deploy git pull
sudo -u deploy docker compose up -d --build
```

Migratsiya (alembic upgrade head) entrypoint ichida avtomatik.

**Diqqat — polling/bot xizmati:** `bot` konteyner qayta ishga tushayotganda
Telegram polling to'xtaydi. Deploy odatda 30-60 soniya. Konfliktdan qochish
uchun kompozitsiyada `app` konteyner polling qilmaydi — faqat `bot` qiladi.

---

## 9. Rollback

Agar deploy'dan keyin xatolik chiqsa:

```bash
cd /opt/student-bot
git log --oneline -5
sudo -u deploy git checkout <old-sha>
sudo -u deploy docker compose up -d --build
```

Migratsiya ORQAGA — agar oxirgi commit'da yangi migratsiya bo'lsa:

```bash
sudo -u deploy docker compose exec app alembic downgrade -1
```

Volume'lar (Postgres, media) tegilmaydi.

Faqat log stack'ni to'xtatish (asosiy ilova ishlab tursin):

```bash
docker compose stop dozzle loki promtail grafana
```

---

## 10. Xavfsizlik eslatmalari

- `.env` faylini hech qachon commit qilmang (`.gitignore` da bor).
- `POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `ADMIN_PASSWORD` — kuchli
  parollar. Almashtirilganda ular `.env` da qoladi, git'ga tushmaydi.
- `docker compose down -v` **hech qachon** avtomatik ishlatilmasin — `-v`
  volume'larni o'chiradi va butun DB yo'qoladi.
- Backup faqat serverda, `/var/backups/student-bot/` da. Off-site ko'chirish
  (S3 yoki boshqa server) — kelajakdagi vazifa.

---

## Aloqa

Muammo bo'lsa `docs/TASKS.md` ga T-4xx sifatida qo'shing.
