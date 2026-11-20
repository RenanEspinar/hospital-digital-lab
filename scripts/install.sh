#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Falta Docker' >&2; exit 1; }
docker compose version >/dev/null || { echo 'Falta docker compose v2' >&2; exit 1; }
if [[ -f .env ]]; then
  echo 'Existe .env; se conservará la configuración actual.'
else
  umask 077
  command -v python3 >/dev/null || { echo 'Falta python3 para generar la clave' >&2; exit 1; }
  PASS="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"
  printf 'ADMIN_PASSWORD=%s\nAPP_BIND=127.0.0.1\nAPP_PORT=8765\n' "$PASS" > .env
  echo 'Clave DOCENTE creada (guárdala en lugar seguro; no se repetirá):'
  echo "$PASS"
fi
echo 'Iniciando el contenedor independiente hospital-digital-lab ...'
docker compose up -d --build
docker compose ps
echo 'Verifica: curl http://127.0.0.1:8765/healthz'
echo 'Para acceso de alumnos remotos, usa un proxy HTTPS seguro con WebSocket.'
