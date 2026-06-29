#!/usr/bin/env bash
# deploy/restore_db.sh
#
# Restores the bookshelf database from a .sql.gz backup file.
#
# Usage:
#   sudo bash deploy/restore_db.sh <backup_file>
#
# Example:
#   sudo bash deploy/restore_db.sh /srv/backups/bookshelf/bookshelf_2026-06-29_02-00-01.sql.gz
#
# WARNING: This DROPS and recreates all tables. All current data will be lost.
#          Stop the bookshelf service before restoring.

set -euo pipefail

ENV_FILE="/srv/bookshelf/.env"
BACKUP_FILE="${1:-}"

# ── Validate input ────────────────────────────────────────────────────────────
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: sudo bash restore_db.sh <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh /srv/backups/bookshelf/*.sql.gz 2>/dev/null || echo "  (none found)"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: File not found: $BACKUP_FILE"
    exit 1
fi

# ── Read DB credentials ───────────────────────────────────────────────────────
_env_val() {
    grep -E "^${1}=" "$ENV_FILE" | head -n1 | sed "s/^${1}=//" | tr -d '"'"'"' '
}

DB_NAME=$(_env_val DB_NAME)
DB_USER=$(_env_val DB_USER)
DB_PASSWORD=$(_env_val DB_PASSWORD)
DB_HOST=$(_env_val DB_HOST)
DB_PORT=$(_env_val DB_PORT)

# ── Confirm ───────────────────────────────────────────────────────────────────
echo "========================================================"
echo "  WARNING: This will OVERWRITE the current database."
echo "  Database : $DB_NAME"
echo "  Backup   : $(basename "$BACKUP_FILE")"
echo "========================================================"
read -p "  Type 'yes' to continue: " confirm
[ "$confirm" = "yes" ] || { echo "Aborted."; exit 0; }

# ── Stop service so no writes happen during restore ───────────────────────────
echo "--> Stopping bookshelf service..."
systemctl stop bookshelf || true

# ── Restore ───────────────────────────────────────────────────────────────────
echo "--> Restoring from $BACKUP_FILE ..."
PGPASSWORD="$DB_PASSWORD" gunzip -c "$BACKUP_FILE" \
    | psql \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --no-password \
        --quiet

echo "--> Restore complete."

# ── Restart service ───────────────────────────────────────────────────────────
echo "--> Restarting bookshelf service..."
systemctl start bookshelf
systemctl is-active --quiet bookshelf \
    && echo "--> Service is running." \
    || echo "--> WARNING: Service failed to start. Check: journalctl -u bookshelf -n 30"
