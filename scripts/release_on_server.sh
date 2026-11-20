#!/usr/bin/env bash
# Publica esta versión en GitHub y luego despliega en homeserverv2 desde Ubuntu.
# No solicita contraseña, token ni modifica otros contenedores.
set -Eeuo pipefail
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-$HOME/apps/hospital-digital-lab}"
REPO="RenanEspinar/hospital-digital-lab"
if [[ ! -d "$TARGET" || ! -f "$TARGET/.env" || ! -f "$TARGET/compose.yaml" ]]; then
  echo 'No encontré la instalación activa con .env y compose.yaml; cancelado.' >&2; exit 1
fi
for command in gh git docker tar python3; do
  command -v "$command" >/dev/null || { echo "Falta $command; cancelado." >&2; exit 1; }
done
gh auth status >/dev/null
GH_LOGIN="$(gh api user --jq '.login')"
if [[ "$GH_LOGIN" != 'RenanEspinar' ]]; then
  echo "GitHub autenticado como $GH_LOGIN, esperaba RenanEspinar; cancelado." >&2; exit 1
fi
gh auth setup-git
TEMP="$(mktemp -d /tmp/hospital-v031-publish.XXXXXXXX)"
trap 'rm -rf "$TEMP"' EXIT
printf '=== 1. Clonando la rama main actual ===\n'
git clone --quiet --depth 1 --branch main "https://github.com/${REPO}.git" "$TEMP/repo"
printf '=== 2. Copiando fuentes y verificando archivos ===\n'
tar -C "$SOURCE" --exclude='./.env' --exclude='./.git' --exclude='./.venv' \
  --exclude='./__pycache__' --exclude='./.pytest_cache' --exclude='*.db' \
  --exclude='*.sqlite' --exclude='*.sqlite3' -cf - . | tar -C "$TEMP/repo" -xf -
git -C "$TEMP/repo" add -A
git -C "$TEMP/repo" diff --cached --check
if git -C "$TEMP/repo" diff --cached --name-only | grep -Eq '(^|/)\.env$|\.(db|sqlite|sqlite3|zip)$|(^|/)(backups|\.venv|__pycache__)/'; then
  echo 'Archivo prohibido en el commit. Se canceló antes de modificar el servidor.' >&2; exit 1
fi
printf '=== 3. Publicando versión en GitHub ===\n'
if ! git -C "$TEMP/repo" diff --cached --quiet; then
  GH_ID="$(gh api user --jq '.id')"
  git -C "$TEMP/repo" config user.name "$GH_LOGIN"
  git -C "$TEMP/repo" config user.email "${GH_ID}+${GH_LOGIN}@users.noreply.github.com"
  git -C "$TEMP/repo" commit -m 'feat: student presence, absence coverage and biomedical inventory v0.3.1'
  git -C "$TEMP/repo" push origin HEAD:main
else
  echo 'GitHub ya contiene la misma versión.'
fi
printf '=== 4. Respaldo SQLite, despliegue de app y verificación ===\n'
bash "$SOURCE/scripts/deploy_safely.sh" "$TARGET"
printf '=== 5. Comprobación del servidor ===\n'
(cd "$TARGET" && docker compose ps)
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8765/healthz
echo
printf 'PUBLICACIÓN Y ACTUALIZACIÓN TERMINADAS\n'
