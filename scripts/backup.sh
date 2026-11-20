#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
STAMP="$(date +%F-%H%M%S)"
TEMP="/data/hospital-backup-${STAMP}.db"
# sqlite3 backup API is safe even with WAL transactions in progress.
docker compose exec -T -e BACKUP_FILE="$TEMP" app python -c \
  "import sqlite3,os; src=sqlite3.connect('/data/hospital.db'); dst=sqlite3.connect(os.environ['BACKUP_FILE']); src.backup(dst); dst.close(); src.close()"
docker compose cp "app:${TEMP}" "./backups/hospital-${STAMP}.db"
docker compose exec -T app rm "$TEMP"
echo "Respaldo creado: backups/hospital-${STAMP}.db"
