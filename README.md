# Hospital Digital Lab

**Simulador educativo multiusuario para HIS, LIS, clínica e ingeniería biomédica.**

Proyecto para las clases de *Innovación, Sistemas de Información y Transformación Digital en la Gestión Biomédica* — Tech Lab Bolivia.

> **SOLO DOCENCIA.** Todos los pacientes, parámetros y resultados son ficticios.
> No se deben introducir datos identificables ni conectar equipos médicos reales.
> Este producto no es un HIS clínico, un LIS certificado ni un dispositivo médico.

## Qué hace esta versión (v0.1)

- **Docente:** crea aulas aisladas con un código independiente, cambia de sala, inicia escenarios y exporta auditoría en CSV.
- **HIS:** admite automáticamente pacientes ficticios y registra sus camas.
- **Enfermería / clínica:** solicita análisis al laboratorio y reconoce alertas clínicas.
- **LIS:** recibe muestras y publica resultados simulados (normales o críticos).
- **Ingeniería biomédica:** simula averías y recuperación de equipos; registra eventos técnicos.
- **Centro de control:** muestra el mapa conceptual del hospital, ocupación, equipos, alarmas, órdenes y acciones de todos los participantes.
- **Tiempo real:** WebSockets con autenticación por primer mensaje y actualización periódica de respaldo.
- **Alarmas:** notificación visual y sonido breve **solo si el usuario lo activa**; no reproduce patrones normativos de alarmas de dispositivos médicos.
- **Evidencia:** bitácora de eventos con mensajes didácticos inspirados en recursos FHIR.

**No implementa** un servidor FHIR interoperable, HL7 v2 de producción, intercambio DICOM, identificación de pacientes real, priorización clínica validada, ni mapas arquitectónicos de hospitales existentes. Las equivalencias del simulador son simplificadas a propósito.

## Requisitos

- Servidor Linux x86-64 o **ARM64** (compatible con Raspberry Pi de 64 bits).
- Docker Engine y **Docker Compose v2**.
- Puerto de escucha local disponible: por defecto `8765`.
- Un proxy HTTPS con WebSockets para acceso de los estudiantes desde internet.

## Instalación en el servidor

```bash
unzip hospital-digital-lab-v0.1.zip
cd hospital-digital-lab
bash scripts/preflight.sh      # Comprueba recursos sin modificar el servidor
bash scripts/install.sh        # Genera una clave docente e inicia Docker
```

Si necesitas personalizar configuración o puerto, revisa `.env` antes de volver a iniciar.

El instalador genera automáticamente una contraseña docente fuerte y la muestra **una sola vez**. Guárdala. Si no usas el instalador, copia `.env.example` a `.env` y cambia manualmente la contraseña.

Comprueba que la aplicación responde:

```bash
docker compose ps
curl http://127.0.0.1:8765/healthz
```

En la **máquina servidor**, abre `http://127.0.0.1:8765`.

### Acceso remoto seguro

El Compose usa por defecto `APP_BIND=127.0.0.1`, por lo que **no publica directamente el servicio en internet**. Configura tu proxy HTTPS existente para apuntar a `http://127.0.0.1:8765` y **permitir WebSockets**. Una vez publicado, comparte con los estudiantes solo la URL **https://...** y el código del aula; **nunca** la clave docente.

Como ejemplo, si administras el dominio, podrías crear `hospital.chuma.website`. **Ese subdominio no está creado por este proyecto.** Comprueba primero la configuración DNS y el proxy de tu servidor. No abras de forma innecesaria los puertos 80/443 ni modifiques contenedores existentes.

No uses `APP_BIND=0.0.0.0` en un servidor conectado directamente a internet sin protección adicional. Para pruebas LAN podría utilizarse temporalmente con cortafuegos adecuado y solo en redes de confianza; el tráfico HTTP y el código de aula **no** sustituyen a HTTPS.

### Acceso si solo dispones de SSH

Desde un ordenador con acceso SSH al servidor:

```bash
ssh -L 8765:127.0.0.1:8765 usuario@192.168.0.39
```

Entonces abre `http://127.0.0.1:8765` en ese ordenador. La IP corresponde al servidor Raspberry conocido anteriormente; **verifica que siga siendo la actual**. Esto no publica la aplicación para toda la clase.

## Cómo dirigir una clase

1. Accede a la URL HTTPS y abre **Docente**.
2. Ingresa la contraseña definida en `.env`.
3. Crea un aula (por ejemplo: `Clase 5 · Grupo 1`).
4. Comparte con los estudiantes el **código** generado.
5. Los estudiantes acceden desde el navegador, ingresan el código, nombre de equipo y rol asignado.
6. **HIS:** agrega un paciente sintético.
7. **Clínica:** envía una solicitud de potasio para ese paciente.
8. **LIS:** recibe la muestra, publica un resultado crítico ficticio.
9. **Clínica:** reconoce la alarma. La bitácora conserva el tiempo transcurrido.
10. **Biomédica:** marca un equipo en falla y posteriormente operativo.
11. Como docente, observa ocupación, dispositivos, alarmas y eventos. Exporta el CSV para analizar indicadores.

> **Importante:** «Reconocer» una alarma no significa que la condición clínica esté resuelta. Los valores críticos son ejemplos numéricos prefijados para clase; no corresponden a criterios clínicos universales ni deben utilizarse en pacientes.

## Estructura del repositorio

```text
hospital-digital-lab/
├── app/
│   ├── main.py                # API FastAPI, autenticación, WebSockets
│   ├── storage.py             # SQLite y lógica de escenarios
│   └── static/
│       ├── index.html         # Interfaz de simulación
│       ├── styles.css
│       └── app.js
├── tests/test_api.py          # Pruebas automatizadas de flujos y aislamiento
├── docs/arquitectura.md       # Modelo de integración y seguridad
├── docs/guia-clase-5.md       # Sesión de indicadores y práctica multiusuario
├── docs/proxy.md              # Publicación HTTPS
├── scripts/install.sh         # Instalación con contraseña generada
├── scripts/preflight.sh       # Inventario no destructivo
├── scripts/backup.sh          # Respaldo del aula
├── compose.yaml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## GitHub

Este ZIP contiene **todo el código fuente**, preparado para crear un repositorio nuevo en tu cuenta.

En una máquina con `git` y `gh` autenticado:

```bash
cd hospital-digital-lab
git init -b main
git add .
git commit -m "feat: simulador educativo HIS LIS multiusuario v0.1"
gh repo create RenanEspinar/hospital-digital-lab --private --source=. --remote=origin --push
```

Si tu cuenta tiene otra identificación, cambia `RenanEspinar`. La opción `--private` evita publicar el código accidentalmente antes de revisarlo. Tras crear el repositorio, puedes hacerlo público si lo deseas.

**El proyecto no crea ni sube automáticamente el repositorio; requiere la ejecución de esos comandos con tu sesión GitHub.** Nunca subas `.env`, respaldos SQLite ni tokens.

## Operaciones y copias

```bash
# Estado y logs
docker compose ps
docker compose logs --tail=100 app

# Actualizar después de cambios en Git
git pull --ff-only
docker compose up -d --build

# Detener sin eliminar la base de datos
docker compose down

# Copia SQLite consistente del volumen del simulador
bash scripts/backup.sh
```

Evita `docker compose down -v`: **borra el volumen persistente** y con él las aulas y su auditoría.

## Protección y limitaciones

- Las sesiones duran 12 horas y los códigos de aula son aleatorios.
- Las aulas se separan mediante controles de autorización del servidor.
- La clave del docente solo se guarda como variable de entorno local.
- Existen límites básicos de intentos y acciones, **pero no son suficientes para un servicio público adversarial**.
- Para uso docente en internet se requiere **HTTPS**, cortafuegos y, preferiblemente, protección adicional en el proxy (rate limiting y controles de acceso).
- SQLite admite grupos pequeños y un único proceso del servidor; no configurar múltiples workers. Para gran escala: PostgreSQL y un bus de eventos (por ejemplo Redis).
- No se incluye respaldo automático ni supervisión continua del servidor. Integrar con las copias que ya administres.
- Todos los datos son sintéticos; está prohibido cargar historiales o información personal real.

## Desarrollo y pruebas

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt pytest httpx
ADMIN_PASSWORD=CLAVE_DE_PRUEBAS_NO_REAL DATABASE_PATH=/tmp/hospital-test.db python -m pytest -q
```

## Referencias técnicas

- [FastAPI: WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Docker Compose](https://docs.docker.com/compose/gettingstarted/)
- [HL7 FHIR — ServiceRequest](https://hl7.org/fhir/R5/servicerequest.html)
- [HL7 FHIR — Observation](https://hl7.org/fhir/R5/observation.html)

Licencia MIT. Este proyecto es un **entorno de simulación educativa**, no un sistema de salud autorizado para operación clínica.
