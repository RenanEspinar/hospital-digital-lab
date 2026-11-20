#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${1:-$HOME/hospital-lab-backups/$STAMP}"
mkdir -p "$DEST"
chmod 700 "$DEST"
tar --exclude='./.env' --exclude='./.git' --exclude='./.venv' --exclude='./backups' -czf "$DEST/source.tar.gz" -C "$PWD" .
CID="$(docker compose ps -q app)"
if [[ -z "$CID" ]]; then echo 'No hay contenedor ejecutándose; se guardó solo el código.'; exit 1; fi
TEMP="/data/hospital-backup-$STAMP.db"
docker compose exec -T -e BACKUP_PATH="$TEMP" app python -c \
 'import os,sqlite3; src=sqlite3.connect("file:/data/hospital.db?mode=ro",uri=True); dest=sqlite3.connect(os.environ["BACKUP_PATH"]); src.backup(dest); dest.close(); src.close()'
docker cp "$CID:$TEMP" "$DEST/hospital.sqlite"
docker compose exec -T -e BACKUP_PATH="$TEMP" app python -c \
 'import os; os.unlink(os.environ["BACKUP_PATH"])'
chmod 600 "$DEST/hospital.sqlite" "$DEST/source.tar.gz"
echo "Respaldo consistente guardado en $DEST"
