# Actualización desde Ubuntu Server — Hospital Digital Lab v0.3.0

**Servidor de trabajo:** `homeserverv2`, directorio `~/apps/hospital-digital-lab`.

No hace falta otra PC, PowerShell ni `rclone` si el servidor permite descargar el ZIP desde Google Drive, como en la versión anterior.

## Despliegue

La versión se distribuye en `hospital-digital-lab-v0.3.0.zip`. Descarga el archivo a `/tmp` con `curl` usando su enlace de Drive. **Verifica SHA-256** antes de descomprimir. Desde el directorio extraído ejecuta:

```bash
bash scripts/release_on_server.sh "$HOME/apps/hospital-digital-lab"
```

Requiere `gh` autenticado como `RenanEspinar`. El script:

1. Clona `main` a una carpeta temporal y copia el código sin `.env`, bases de datos ni secretos.
2. Valida los archivos y publica un commit en GitHub.
3. Hace un respaldo SQLite consistente mediante el contenedor actual a `~/hospital-lab-backups/antes-de-v03-.../` y guarda una copia del código.
4. Actualiza **solo el servicio `app`** de Docker y espera una respuesta `healthz` con `version: 0.3.0`.

Si falla el push, no se inicia el despliegue. Si Docker no inicia, **el script no aplica rollback automático**: revisa `docker compose logs --tail=100 app` y conserva el respaldo. Nunca uses `docker compose down -v`.

## Verificación

```bash
cd ~/apps/hospital-digital-lab
docker compose ps
curl -fsS http://127.0.0.1:8765/healthz
```

Se espera `"version":"0.3.0"` y un contenedor saludable. Después valida en navegador el panel docente: distribución 3/4 estudiantes, guardar, un incidente con Farmacia/Imagenología virtual y actuación humana de Clínica.

## Compatibilidad

La migración agrega `role_staffing` y no elimina tablas existentes ni aulas. La configuración inicial de las aulas previas permanece con seis roles humanos. El acceso HTTPS/proxy, la clave `ADMIN_PASSWORD` y el volumen de SQLite permanecen intactos.
