#!/usr/bin/env bash
# Actualiza la instalación existente sin eliminar su volumen ni tocar .env.
set -euo pipefail
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$HOME/apps/hospital-digital-lab}"
TARGET="$(cd "$TARGET" 2>/dev/null && pwd)" || { echo "No existe el directorio destino." >&2; exit 1; }
if [[ "$SOURCE" == "$TARGET" ]]; then echo 'Origen y destino no deben coincidir.' >&2; exit 1; fi
if [[ ! -f "$TARGET/compose.yaml" || ! -f "$TARGET/.env" ]]; then
  echo "Instalación incompleta en $TARGET (compose.yaml o .env ausente)." >&2; exit 1
fi
command -v docker >/dev/null || { echo 'Docker no está instalado.' >&2; exit 1; }
(cd "$TARGET" && docker compose version >/dev/null)
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$HOME/hospital-lab-backups/antes-de-v031-$STAMP"
mkdir -p "$BACKUP"
chmod 700 "$BACKUP"
echo '1/4 Respaldo del código actual y SQLite desde contenedor activo'
tar --exclude='./.env' --exclude='./.git' --exclude='./.venv' --exclude='./__pycache__' \
  --exclude='./.pytest_cache' --exclude='./backups' -czf "$BACKUP/source.tar.gz" -C "$TARGET" .
CID="$(cd "$TARGET" && docker compose ps -q app)"
if [[ -z "$CID" ]] || ! docker inspect -f '{{.State.Running}}' "$CID" | grep -qx true; then
  echo 'Contenedor previo no está ejecutándose. No se instalará sin respaldo SQLite consistente.' >&2
  exit 1
fi
TEMP="/data/hospital-backup-$STAMP.db"
(cd "$TARGET" && docker compose exec -T -e BACKUP_PATH="$TEMP" app python -c \
 'import os,sqlite3; src=sqlite3.connect("file:/data/hospital.db?mode=ro",uri=True); dst=sqlite3.connect(os.environ["BACKUP_PATH"]); src.backup(dst); dst.close(); src.close()')
docker cp "$CID:$TEMP" "$BACKUP/hospital.sqlite"
(cd "$TARGET" && docker compose exec -T -e BACKUP_PATH="$TEMP" app python -c \
 'import os; os.unlink(os.environ["BACKUP_PATH"])')
chmod 600 "$BACKUP/source.tar.gz" "$BACKUP/hospital.sqlite"
python3 - "$BACKUP/hospital.sqlite" <<'PY'
import sqlite3, sys
cx = sqlite3.connect(sys.argv[1])
assert cx.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Respaldo SQLite dañado'
cx.close()
print('Respaldo SQLite verificado correctamente.')
PY
# Conservar imagen anterior para recuperación rápida sin reinstalar dependencias.
PREVIOUS_IMAGE_ID="$(docker inspect -f '{{.Image}}' "$CID")"
ROLLBACK_TAG="hospital-digital-lab:rollback-$STAMP"
docker tag "$PREVIOUS_IMAGE_ID" "$ROLLBACK_TAG"
rollback_on_error() {
  STATUS=$?
  trap - ERR
  set +e
  echo 'ACTUALIZACIÓN FALLIDA: intentando recuperar automáticamente la versión anterior.' >&2
  tar -xzf "$BACKUP/source.tar.gz" -C "$TARGET"
  docker tag "$ROLLBACK_TAG" hospital-digital-lab:local
  (cd "$TARGET" && docker compose up -d --no-deps --force-recreate app)
  (cd "$TARGET" && docker compose ps)
  echo "Respaldo seguro: $BACKUP" >&2
  echo 'El SQLite de respaldo queda intacto. No se restaura automáticamente porque podría descartar operaciones posteriores al respaldo.' >&2
  exit "$STATUS"
}
trap rollback_on_error ERR

echo '2/4 Copia de los archivos nuevos, preservando .env y volumen'
tar -C "$SOURCE" -cf - \
 --exclude='./.env' --exclude='./.git' --exclude='./.venv' \
 --exclude='./__pycache__' --exclude='./.pytest_cache' . | tar -C "$TARGET" -xf -
# Un entrypoint anterior no permanece activo: v0.3.1 usa el CMD del nuevo Dockerfile.
echo '3/4 Construcción y actualización SOLO del servicio app'
(cd "$TARGET" && docker compose config -q && docker compose up -d --build --no-deps app)
echo '4/4 Verificación de salud'
(cd "$TARGET" && docker compose exec -T app python -c \
 'import json,time,urllib.request; last=None
for _ in range(45):
 try:
  x=json.load(urllib.request.urlopen("http://127.0.0.1:8000/healthz",timeout=3))
  assert x["version"]=="0.3.1",x
  print("Servicio OK:",x); break
 except Exception as e: last=e; time.sleep(2)
else: raise SystemExit("Falló comprobación de salud: "+str(last))')
trap - ERR
printf '\nActualización terminada. Respaldo anterior: %s\n' "$BACKUP"
printf 'Imagen anterior conservada: %s\n' "$ROLLBACK_TAG"
