# Actualización segura v0.3.1 — homeserverv2 (Ubuntu)

**No ejecutar mientras los estudiantes trabajan.** Requiere acceso por SSH a `~/apps/hospital-digital-lab`, credenciales de GitHub `gh` ya configuradas y Docker Compose v2.

- Descargar el ZIP y comprobar SHA-256 antes de ejecutar el script. No descargar ejecutables de URL diferentes a la compartida por el docente.
- Extraer el ZIP en un directorio temporal y ejecutar `bash scripts/release_on_server.sh "$HOME/apps/hospital-digital-lab"` desde la carpeta extraída.
- El script publica en GitHub `RenanEspinar/hospital-digital-lab` y despliega únicamente `app`, nunca otros contenedores.
- Antes de copiar, el instalador guarda `source.tar.gz` y respaldo consistente `hospital.sqlite` en `~/hospital-lab-backups/antes-de-v031-...` con permisos restrictivos. Conserva también una etiqueta de la imagen Docker anterior `hospital-digital-lab:rollback-...`.
- Ante fallo en la actualización o en `/healthz`, intenta regresar el código y la imagen anteriores. El respaldo SQLite no se restaura automáticamente porque eso podría descartar nuevas operaciones. Si el servicio sigue inaccesible tras el intento, conservar la carpeta de respaldo y solicitar reparación antes de impartir clase.
- La migración de esquema SQLite es aditiva y conserva aulas, pacientes, órdenes, incidentes, sesiones y auditoría anteriores. No ejecutar `docker compose down -v`.

Validación final en el servidor:

```bash
cd ~/apps/hospital-digital-lab
docker compose ps
curl -fsS http://127.0.0.1:8765/healthz
# Debe indicar version: 0.3.1
```

Validar interfaz: entrar como docente, seleccionar un aula de pruebas, elegir **3 estudiantes** y verificar que aparecen seis departamentos. Acceder desde un segundo navegador como LIS y confirmar que aparece el nombre y estado conectado; abrir **Equipamiento** y editar una ficha ficticia; registrar una nota de prueba; generar manualmente un incidente. Se recomienda dejar `Cubrir ausencias automáticamente` desactivado hasta terminar esa comprobación.

**Limitaciones conocidas:** el conteo de conexión es actividad reciente, no telemetría de enlace; los bots no sustituyen un juicio clínico. Datos ficticios exclusivamente.
