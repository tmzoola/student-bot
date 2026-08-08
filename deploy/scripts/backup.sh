#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# student-bot kunlik backup
#
# - Postgres dump  → /var/backups/student-bot/db-YYYY-MM-DD.sql.gz
# - Media volume   → /var/backups/student-bot/media-YYYY-MM-DD.tar.gz
# - Retention      : 7 kundan eski fayllar o'chiriladi
#
# Cron (deploy foydalanuvchisi ostida):
#   0 3 * * * /opt/student-bot/deploy/scripts/backup.sh \
#             >> /var/log/student-bot-backup.log 2>&1
#
# Idempotent: xuddi shu kunda ikkinchi marta ishga tushirilsa faylni qayta yozadi.
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/student-bot}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/student-bot}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-student-bot}"   # docker volume prefiksi

DATE="$(date +%F)"
TS="$(date -Is)"

echo "[$TS] student-bot backup boshlandi"

mkdir -p "$BACKUP_DIR"

# ── .env dan POSTGRES_* o'zgaruvchilarni yuklash ─────────────────────
if [[ -f "$PROJECT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "!! $PROJECT_DIR/.env topilmadi" >&2
    exit 1
fi

: "${POSTGRES_USER:?POSTGRES_USER bo'sh}"
: "${POSTGRES_DB:?POSTGRES_DB bo'sh}"

cd "$PROJECT_DIR"

# ── 1. Postgres dump ─────────────────────────────────────────────────
DB_FILE="$BACKUP_DIR/db-$DATE.sql.gz"
echo "[$TS] pg_dump → $DB_FILE"
# -T flag TTY talab qilmaydi (cron muhitida shart).
if ! docker compose exec -T db \
        pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --no-owner --no-privileges | gzip -9 > "$DB_FILE.tmp"; then
    echo "!! pg_dump muvaffaqiyatsiz" >&2
    rm -f "$DB_FILE.tmp"
    exit 1
fi
mv "$DB_FILE.tmp" "$DB_FILE"

# ── 2. Media volume ──────────────────────────────────────────────────
# Volume nomini Compose loyihasi asosida topamiz. Odatda `<project>_media_data`.
MEDIA_VOLUME="${COMPOSE_PROJECT}_media_data"
MEDIA_FILE="$BACKUP_DIR/media-$DATE.tar.gz"
echo "[$TS] media volume ($MEDIA_VOLUME) → $MEDIA_FILE"

if ! docker volume inspect "$MEDIA_VOLUME" >/dev/null 2>&1; then
    # Compose ba'zan volume'ni boshqa prefiks bilan yaratadi (masalan
    # `student_bot_media_data`). Ro'yxatdan topib olamiz.
    MEDIA_VOLUME="$(docker volume ls -q | grep -E 'media_data$' | head -n1 || true)"
    if [[ -z "$MEDIA_VOLUME" ]]; then
        echo "!! media volume topilmadi, o'tkazib yuborildi" >&2
        MEDIA_FILE=""
    fi
fi

if [[ -n "${MEDIA_FILE:-}" ]]; then
    # Volume'ni alohida konteynerda mount qilib arxivlaymiz.
    docker run --rm \
        -v "$MEDIA_VOLUME:/data:ro" \
        -v "$BACKUP_DIR:/backup" \
        alpine:3.20 \
        tar czf "/backup/media-$DATE.tar.gz.tmp" -C /data .
    mv "$MEDIA_FILE.tmp" "$MEDIA_FILE"
fi

# ── 3. Retention (7 kundan eski) ─────────────────────────────────────
echo "[$TS] retention: $RETENTION_DAYS kundan eski fayllarni o'chirish"
find "$BACKUP_DIR" -maxdepth 1 -type f \
    \( -name 'db-*.sql.gz' -o -name 'media-*.tar.gz' \) \
    -mtime +"$RETENTION_DAYS" -print -delete

# ── 4. Xulosa ────────────────────────────────────────────────────────
echo "[$TS] joriy backup fayllari:"
ls -lh "$BACKUP_DIR" | tail -n +2

echo "[$TS] backup muvaffaqiyatli yakunlandi"
