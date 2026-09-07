#!/usr/bin/env bash
# Резервная копия базы заявок. Запускать на хосте, например из cron:
#   0 3 * * * /path/to/scripts/backup_db.sh >> /var/log/leadbot-backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$(dirname "$0")/../backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
DB_USER="${POSTGRES_USER:-leadbot}"
DB_NAME="${POSTGRES_DB:-leadbot}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="$BACKUP_DIR/leadbot_$STAMP.sql.gz"

echo "→ Снимаю дамп базы $DB_NAME в $TARGET"
docker compose exec -T postgres pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$TARGET"

echo "→ Удаляю копии старше $KEEP_DAYS дней"
find "$BACKUP_DIR" -name 'leadbot_*.sql.gz' -mtime +"$KEEP_DAYS" -delete

echo "✓ Готово: $(du -h "$TARGET" | cut -f1)"
