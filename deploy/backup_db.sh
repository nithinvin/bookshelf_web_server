#!/usr/bin/env bash
# deploy/backup_db.sh
#
# Backs up the bookshelf PostgreSQL database to /srv/backups/bookshelf/.
# Retains the last KEEP_DAYS days of backups and deletes older ones.
#
# Usage:
#   sudo bash deploy/backup_db.sh            # manual run
#   (runs automatically via cron — see DEPLOY.md)
#
# Backup location : /srv/backups/bookshelf/
# File naming     : bookshelf_2026-06-29_14-30-00.sql.gz
# Retention       : 3 days (change KEEP_DAYS below)

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
ENV_FILE="/srv/bookshelf/.env"
BACKUP_DIR="/srv/backups/bookshelf"
KEEP_DAYS=3
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/bookshelf_${TIMESTAMP}.sql.gz"
LOG_FILE="/var/log/bookshelf/backup.log"

# ── Read DB credentials from .env ─────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $ENV_FILE not found." | tee -a "$LOG_FILE"
    exit 1
fi

_env_val() {
    grep -E "^${1}=" "$ENV_FILE" | head -n1 | sed "s/^${1}=//" | tr -d '"'"'"' '
}

DB_NAME=$(_env_val DB_NAME)
DB_USER=$(_env_val DB_USER)
DB_PASSWORD=$(_env_val DB_PASSWORD)
DB_HOST=$(_env_val DB_HOST)
DB_PORT=$(_env_val DB_PORT)

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: DB_NAME or DB_USER missing in $ENV_FILE." | tee -a "$LOG_FILE"
    exit 1
fi

# ── Create backup directory if it doesn't exist ───────────────────────────────
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"   # only root can read backup files

# ── Run pg_dump and compress ──────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting backup → $BACKUP_FILE" >> "$LOG_FILE"

PGPASSWORD="$DB_PASSWORD" pg_dump \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --format=plain \
    --no-password \
    "$DB_NAME" \
    | gzip -9 > "$BACKUP_FILE"

# Verify the file was created and is non-empty
if [ ! -s "$BACKUP_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup file is empty or missing." | tee -a "$LOG_FILE"
    exit 1
fi

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup complete. Size: $SIZE" >> "$LOG_FILE"

# ── Delete backups older than KEEP_DAYS ───────────────────────────────────────
DELETED=$(find "$BACKUP_DIR" \
    -maxdepth 1 \
    -name "bookshelf_*.sql.gz" \
    -mtime "+${KEEP_DAYS}" \
    -print \
    -delete \
    | wc -l)

if [ "$DELETED" -gt 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deleted $DELETED backup(s) older than ${KEEP_DAYS} days." >> "$LOG_FILE"
fi

# ── List retained backups ─────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Retained backups:" >> "$LOG_FILE"
find "$BACKUP_DIR" -maxdepth 1 -name "bookshelf_*.sql.gz" \
    | sort | while read -r f; do
    echo "    $(basename "$f")  ($(du -sh "$f" | cut -f1))" >> "$LOG_FILE"
done

echo "---" >> "$LOG_FILE"
