#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .env ]]; then echo 'Ya existe .env: no se reemplaza ni se revela la contraseña.'; else
  command -v python3 >/dev/null || { echo 'Falta python3'; exit 1; }
  python3 - <<'PY'
from pathlib import Path
from secrets import token_urlsafe
password=token_urlsafe(32)
Path('.env').write_text('ADMIN_PASSWORD='+password+'\nAPP_BIND=127.0.0.1\nAPP_PORT=8765\n')
Path('.env').chmod(0o600)
print('Contraseña docente generada (guárdala de forma privada): '+password)
PY
fi
docker compose up -d --build
printf 'Comprobar con: docker compose ps\n'
