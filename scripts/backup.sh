#!/bin/bash
set -e

BACKUP_DIR="/app/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_PATH="${WHOOP_DB_PATH:-/app/data/whoop.db}"
TOKENS_PATH="${WHOOP_TOKENS_FILE:-/app/tokens.json}"
RETENTION_DAYS=${RETENTION_DAYS:-30}

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$BACKUP_DIR/whoop_$TIMESTAMP.db"
    gzip "$BACKUP_DIR/whoop_$TIMESTAMP.db"
    echo "[$(date)] Database backed up: whoop_$TIMESTAMP.db.gz"
fi

if [ -f "$TOKENS_PATH" ]; then
    cp "$TOKENS_PATH" "$BACKUP_DIR/tokens_$TIMESTAMP.json"
    echo "[$(date)] Tokens backed up: tokens_$TIMESTAMP.json"
fi

find "$BACKUP_DIR" -name "*.db.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "tokens_*.json" -mtime +$RETENTION_DAYS -delete

BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.db.gz 2>/dev/null | wc -l)
echo "[$(date)] Backup complete. Total backups: $BACKUP_COUNT"
