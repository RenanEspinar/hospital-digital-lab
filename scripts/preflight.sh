#!/usr/bin/env bash
set -euo pipefail
printf '\nHospital Digital Lab v0.2 · Preflight (solo lectura)\n'
command -v docker >/dev/null || { echo 'Falta docker'; exit 1; }
docker compose version
command -v python3 >/dev/null && python3 --version || true
printf 'Directorio: %s\n' "$PWD"
printf 'Estado de Docker:\n'
docker info --format 'Servidor: {{.ServerVersion}} / {{.Architecture}}' || true
printf 'Preflight terminado. No se cambió nada.\n'
