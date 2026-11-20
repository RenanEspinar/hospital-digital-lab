#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo '=== HOSPITAL DIGITAL / COMPROBACIÓN NO DESTRUCTIVA ==='
echo "Host: $(hostname)"
echo "Arquitectura: $(uname -m)"
echo "Kernel: $(uname -r)"
echo '--- Docker ---'
docker --version
if ! docker compose version; then
  echo 'Se necesita Docker Compose v2.' >&2
  exit 1
fi
echo '--- Puertos TCP escuchando (comprueba el 8765) ---'
if command -v ss >/dev/null; then
  ss -ltn | grep -E '(:8765|:8090|:80 |:443 )' || true
else
  echo 'Comando ss no disponible.'
fi
echo '--- Memoria y disco ---'
free -h || true
df -h . || true
echo '--- Servicios existentes (solo lectura) ---'
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo 'No se realizaron cambios.'
