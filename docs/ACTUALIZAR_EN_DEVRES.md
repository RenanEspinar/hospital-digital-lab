# Actualizar en el servidor `devres` (o el host SSH equivalente)

## Orden recomendado

**1.** Descarga el paquete `hospital-digital-lab-v0.2.2.zip` de Drive a tu computadora y transfiérelo por SSH/SCP a tu servidor. Sustituye el nombre de host por tu alias SSH real si `devres` no resuelve.

```bash
scp hospital-digital-lab-v0.2.2.zip renan@devres:/tmp/
```

**2.** En una sesión SSH de `devres`, verifica la instalación previa y expande el ZIP en el directorio de trabajo:

```bash
ssh renan@devres
cd ~/apps/hospital-digital-lab
docker compose ps
curl -fsS http://127.0.0.1:8765/healthz

cd ~/apps
unzip -q /tmp/hospital-digital-lab-v0.2.2.zip
```

**3.** Ejecuta la actualización segura. El script crea antes un respaldo consistente de la base SQLite y un paquete del código actual en `~/hospital-lab-backups/`. Conserva el archivo `.env`, usuarios docentes, aulas y volumen Docker.

```bash
bash ~/apps/hospital-digital-lab-v0.2.2/scripts/deploy_safely.sh "$HOME/apps/hospital-digital-lab"
```

**4.** Revisa el resultado y la URL del proxy que ya utilizas:

```bash
cd ~/apps/hospital-digital-lab
docker compose ps
docker compose logs --tail=80 app
curl -fsS http://127.0.0.1:8765/healthz
```

La respuesta esperada incluye `"version":"0.2.2"`. Si tienes un puerto personalizado, usa el valor de `APP_PORT` de `.env`.

## Respuesta a incidentes de despliegue

Si el nuevo contenedor no inicia, conserva intactos los respaldos. El script detiene su ejecución al fallar, **no ejecuta un rollback automático**. Antes de revertir, revisa `docker compose logs app` y el contenido de `~/hospital-lab-backups/antes-de-v02-.../`.

Para revertir, restaura el código desde `source.tar.gz` y la base de datos desde `hospital.sqlite` con el contenedor detenido. El lugar exacto del volumen debe comprobarse mediante `docker volume inspect` antes de escribir: no adivines nombres de volúmenes ni borres el volumen con `down -v`.

## Código publicado en GitHub

El código fuente de esta versión está disponible en el repositorio `RenanEspinar/hospital-digital-lab`. No es necesario ejecutar `git add` o `git push` desde el servidor para publicar esta actualización.

Si prefieres obtener el código mediante GitHub en lugar de descargar el ZIP, utiliza un clon temporal, separado de la instalación activa, y ejecuta el mismo script de respaldo y actualización:

```bash
cd ~/apps
git clone --depth 1 https://github.com/RenanEspinar/hospital-digital-lab.git hospital-digital-lab-release
bash ~/apps/hospital-digital-lab-release/scripts/deploy_safely.sh "$HOME/apps/hospital-digital-lab"
```

**Nota:** el instalador preserva la carpeta `.git` que exista en el destino; si se instaló mediante copia de archivos, puede quedar con cambios locales respecto a su rama. No ejecutes `git reset --hard`, `git clean -fd` ni `docker compose down -v` sobre el proyecto activo sin revisar su estado.

## Seguridad de los alumnos

Comparte la URL **HTTPS** y el código de aula, nunca la contraseña de `.env`. El simulador sigue usando datos ficticios y no autentica identidades institucionales.
