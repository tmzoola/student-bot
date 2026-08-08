# Deploy va monitoring — DevOps uchun qo'llanma

Bu dokument log/monitoring stack'ini production'ga tushirish bo'yicha aniq
qadamlar. `main` branch'idagi kod deploy'ga tayyor.

Domain: **ob-malaka.timv.uz**

---

## 1. Yangi konteynerlar

`docker-compose.yml` da yangi 4 ta xizmat qo'shildi:

| Servis | Port (ichki) | Vazifasi | RAM |
|--------|--------------|----------|-----|
| `dozzle` | 8080 | Real-vaqt log UI | ~30 MB |
| `loki` | 3100 | Log ma'lumotlar bazasi | ~200 MB |
| `promtail` | — | Konteyner log'larini Loki'ga uzatuvchi | ~50 MB |
| `grafana` | 3000 | Dashboard + tarixiy tahlil + alerting | ~150 MB |

Barcha yangi portlar **`expose`** orqali faqat compose ichida. Tashqariga faqat
Nginx orqali chiqadi. Loki'ni to'g'ridan-to'g'ri ochmang.

Barcha eski (`db`, `redis`, `app`, `bot`, `guard`) xizmatlarga **log rotation**
qo'shildi: har konteyner max 250 MB log ushlaydi (50 MB × 5 fayl, gzip
siqilgan). Disk to'lish xavfi endi yo'q.

---

## 2. `.env` ga qo'shiladigan o'zgaruvchilar

Production `.env` faylida quyidagi qatorlar bo'lishi shart (agar yo'q bo'lsa
qo'shing):

```env
# Redis (Docker Compose ichidagi service)
REDIS_URL=redis://redis:6379/0

# Grafana admin
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123
```

**Grafana parolini keyinchalik almashtiring** (kuchli parol qo'ying), keyin
`docker compose up -d grafana` bilan qayta ishga tushiring.

---

## 3. Nginx sozlamasi

`ob-malaka.timv.uz` konfiguratsiyasiga quyidagi bloklarni qo'shing:

```nginx
# ── Dozzle: real-vaqt log UI ────────────────────────────────────
# Nginx basic auth bilan himoyalanadi (Dozzle o'z auth'i yo'q).
location /logs/ {
    auth_basic "Log viewer";
    auth_basic_user_file /etc/nginx/.htpasswd_logs;

    proxy_pass http://127.0.0.1:8080/logs/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Dozzle real-vaqt log streaming uchun WebSocket
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600;
    proxy_buffering off;
}

# ── Grafana: dashboard, tarix, alerting ────────────────────────
# Grafana o'z login'i bor (admin/admin123), qo'shimcha basic auth kerak emas.
location /grafana/ {
    proxy_pass http://127.0.0.1:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Grafana Live features (real-vaqt dashboard yangilanishi)
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600;
}
```

Basic auth fayl yaratish:
```bash
# apache2-utils o'rnatilmagan bo'lsa: apt install apache2-utils
htpasswd -c /etc/nginx/.htpasswd_logs admin
# Parol so'raydi — masalan: admin123
```

Sozlagach:
```bash
nginx -t                # sintaksis tekshirish
systemctl reload nginx  # yangilash
```

---

## 4. Ishga tushirish qadamlari

Bir marta bajarish:

```bash
# 1. Kodni yangilash
cd /path/to/edu-bot
git pull

# 2. Yangi xizmatlarni ko'tarish (jami ~450 MB RAM ishlatadi)
docker compose up -d --build

# 3. Barchasi ishga tushganini tekshirish (30-60 sek kutish kerak)
docker compose ps
# Kutilayotgan xizmatlar (Status: healthy):
#   malaka_db, malaka_redis, malaka_app, malaka_bot,
#   malaka_dozzle, malaka_loki, malaka_promtail, malaka_grafana

# 4. Health tekshirish
curl -s http://localhost:8000/health | python3 -m json.tool
# Kutilgan: db.ok=true, redis.ok=true, pool.size=20

# 5. Loki log qabul qilyaptimi
curl -s "http://localhost:3100/loki/api/v1/labels" | jq
# Kutilgan: {"status":"success","data":["container","filename",...]}

# 6. Nginx sozlash (yuqoridagi bo'lim)

# 7. Brauzerda tekshirish
# https://ob-malaka.timv.uz/logs      → Dozzle (basic auth admin)
# https://ob-malaka.timv.uz/grafana   → Grafana login (admin/admin123)
```

---

## 5. Grafana birinchi kirishdan keyin

1. `https://ob-malaka.timv.uz/grafana` — login: `admin`/`admin123`.
2. **Explore** (chap panelda kompas ikonasi) → Datasource: **Loki** → Query:
   ```
   {container="malaka_app"}
   ```
   Log oqim ko'rinishi kerak.
3. **Dashboards** → **New** → **Import** → ID `13639` (Loki Metrics) yoki
   `15140` (Docker Container Logs). Datasource: Loki.
4. **Alerting** (soat ikonasi) → **Notification channels** → **New channel**
   → Type: Telegram. Bot token va chat_id kiriting. Test qiling.
5. Alert qoidalari (misol):
   - "Har 5 daqiqada `error` yoki `timeout` matni > 20 ta" → Telegram xabar.
   - "`/health` endpoint 3 marta ketma-ket 5xx qaytarsa" → Telegram xabar.

---

## 6. Yaqin muddatli tekshiruv (ishga tushirilgan zahoti)

```bash
# Barcha konteyner UP
make logs-all

# Xatolar yo'qmi
make logs-errors
make logs-timeouts
make logs-conflict

# DB va Redis holati
make db-connections
make redis-info

# App health
make health
```

Xatolar ro'yxati:

- `logs-conflict` bo'sh bo'lishi kerak — aks holda ikkita bot polling ishlayapti
  (eski `app` konteyner to'xtamagan).
- `db-connections` da active > 100 bo'lsa — connection leak yoki juda katta
  yuklama, pool sozlamalarini qayta ko'rish.
- `redis-info` da `keyspace_hits/keyspace_misses` nisbat > 5 bo'lsa yaxshi
  (subscription kesh ishlayapti).

---

## 7. Ma'lumot yo'qolish xavfi va rollback

**Ma'lumot yo'qolmaydi:**
- Postgres volume o'zgarmadi (`postgres_data`).
- Media volume o'zgarmadi (`media_data`).
- Yangi Loki/Grafana volumelar bo'sh — birinchi marta ma'lumot yig'iladi.

**Rollback (agar biror narsa noto'g'ri bo'lsa):**
```bash
git log --oneline -5     # oxirgi commit'lardan biriga
git revert HEAD          # yoki git checkout <old-commit>
docker compose down
docker compose up -d --build
```

Log xizmatlarini alohida o'chirish (asosiy stack ta'sirlanmaydi):
```bash
docker compose stop dozzle loki promtail grafana
docker compose rm -f dozzle loki promtail grafana
```

---

## 8. Kelajakda sozlash arziydigan narsalar

- **Grafana parolini almashtirish** (birinchi kirishdan so'ng).
- **Loki retention** — hozir 30 kun. Disk tez to'ladigan bo'lsa
  `observability/loki-config.yaml` da `retention_period: 168h` (7 kun) qiling.
- **Dashboard'lar** — dastlab tayyor template'lardan foydalaning, keyinchalik
  loyihaga xos panellar qo'shing (contest paytida savol yechish tezligi,
  xatolar chastotasi, va h.k.).
- **Alert qoidalari** — event kunidan oldin sinab ko'ring.
- **Backup** — Grafana dashboard'larni JSON'ga eksport qilib repositoriyga
  saqlang.

---

## Aloqa

Savol bo'lsa: `docs/TASKS.md` ga T-xxx sifatida qo'shing yoki chatda ayting.

---

## 9. Haqiqiy deploy holati (2026-07-27, ob-malaka.timv.uz serveri)

Deploy bajarildi. Quyida yuqoridagi ko'rsatmalardan **farq qilgan** joylar —
keyingi safar shu bo'limga tayaning, 3-bo'limdagi nginx snippet'i bu serverda
to'g'ridan-to'g'ri ishlamaydi.

### 9.1. Portlar: `expose` yetarli emas edi

1-bo'limda "barcha yangi portlar `expose` orqali" deyilgan, lekin nginx host'da
(konteynerda emas) ishlaydi — `expose` host'ning `127.0.0.1` iga port ochmaydi,
shuning uchun `proxy_pass http://127.0.0.1:8080` hech qayerga bormasdi.

Yechim — `docker-compose.yml` da loopback binding qo'shildi (tashqariga baribir
ochilmaydi, faqat host ichidan):

```yaml
dozzle:
  ports:
    - "127.0.0.1:8080:8080"
grafana:
  ports:
    - "127.0.0.1:3001:3000"
```

> **Grafana 3000 EMAS, 3001.** Host'ning 3000-porti PM2 ostidagi boshqa ilova
> tomonidan band. 3-bo'limdagidek `127.0.0.1:3000` ga proxy qilinsa, Grafana
> o'rniga o'sha begona ilova ochiladi.

### 9.2. Grafana `proxy_pass` da oxirgi slash BO'LMASLIGI kerak

Compose'da `GF_SERVER_SERVE_FROM_SUB_PATH: "true"` turibdi — ya'ni Grafana
`/grafana` prefiksini o'zi kutadi. 3-bo'limdagi `proxy_pass http://...:3000/;`
(slash bilan) prefiksni kesib tashlaydi, natijada Grafana `/grafana/` ga qayta
yo'naltiradi va **redirect loop** hosil bo'ladi.

To'g'risi — slashsiz:

```nginx
location /grafana/ {
    proxy_pass http://127.0.0.1:3001;   # oxirida / YO'Q
    ...
}
```

### 9.3. `Connection "upgrade"` o'rniga map

Har bir so'rovda qat'iy `Connection: upgrade` yuborish websocket bo'lmagan
so'rovlarni buzishi mumkin. `/etc/nginx/conf.d/websocket_upgrade.conf` da umumiy
map yaratildi va ikkala blokda `proxy_set_header Connection $connection_upgrade;`
ishlatiladi.

### 9.4. `/logs` va `/grafana` (slashsiz) uchun redirect

`location /logs/` slashsiz `/logs` so'rovini ushlamaydi — u `location /` ga
tushib app'dan 404 olardi. Qo'shildi:

```nginx
location = /logs    { return 301 /logs/; }
location = /grafana { return 301 /grafana/; }
```

### 9.5. Dozzle healthcheck tuzatildi

Compose'dagi `wget`-ga asoslangan healthcheck ishlamasdi (Dozzle image'i
distroless, ichida `wget` yo'q) — konteyner doim `unhealthy` turardi.
Endi Dozzle'ning o'z buyrug'i:

```yaml
healthcheck:
  test: ["CMD", "/dozzle", "healthcheck"]
```

### 9.6. Parollar — `admin123` EMAS

Ochiq domendagi Grafana uchun `admin123` xavfli, shuning uchun kuchli parollar
qo'yildi (`.env` va `/etc/nginx/.htpasswd_logs` da). Parollarni serverdan
qarang, bu faylga yozmang:

```bash
grep GRAFANA_ADMIN /opt/bot/edu-bot/.env
```

> Diqqat: `GF_SECURITY_ADMIN_PASSWORD` faqat Grafana bazasi **birinchi marta**
> yaratilganda qo'llanadi. Volume mavjud bo'lsa `.env` ni o'zgartirish yetarli
> emas — parolni shunday almashtiring:
> ```bash
> docker exec malaka_grafana grafana cli --homepath /usr/share/grafana \
>     admin reset-admin-password '<yangi-parol>'
> ```

### 9.7. Bu serverda `docker compose` emas, `docker-compose`

O'rnatilgan versiya Compose v1.29.0 (Docker 20.10.12). Yuqoridagi barcha
`docker compose ...` buyruqlarini `docker-compose ...` deb yozing.

### 9.8. Hali bajarilmagan (qo'lda talab qiladi)

- **5-bo'lim: dashboard import** (ID `13639` / `15140`) — Grafana'dan
  grafana.com ga chiqish kerak, brauzerdan qilinadi.
- **5-bo'lim: Telegram alerting** — bot token va chat_id kerak, ular yo'q edi.
- **Disk**: `/` 81% to'lgan (13 GB bo'sh). Loki retention 30 kun — agar disk
  siqilsa `observability/loki-config.yaml` da `retention_period: 168h` qiling.
