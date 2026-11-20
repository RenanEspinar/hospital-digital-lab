# Hospital Digital Lab · v0.3.1

Simulador web educativo multiusuario para formación en sistemas hospitalarios, ingeniería biomédica, operación e interoperabilidad didáctica. **No es un sistema clínico real.** Pacientes, alarmas, parámetros, órdenes e informes son sintéticos. No se permite cargar datos personales, usar decisiones del simulador con pacientes ni conectar dispositivos médicos.

## Novedad v0.3.1 — Personal presente, suplencias y activos biomédicos

El docente ve en cada aula **estudiantes conectados por nombre y rol**. Una sesión se considera activa cuando registra actividad durante los últimos **45 segundos**. El botón «Automatizar» de cada departamento toma el relevo inmediatamente; «Devolver a estudiante» permite recuperar el control. Se conserva la configuración previa de roles humanos y bots permanentes.

La opción **«Cubrir ausencias automáticamente (60 s)»** está **desactivada por defecto**. Si se activa, tras 60 segundos sin actividad de un rol humano el simulador activa un bot de suplencia; cuando el estudiante vuelve a ingresar o retoma su sesión, recupera el control automáticamente. El sistema no desplaza a los bots permanentes ni asigna roles diferentes a los del aula. El plazo depende de los latidos de la sesión y del motor de 5 segundos, no equivale a un SLA clínico.

El inventario contiene **10 equipos de práctica** en nuevas aulas y actualiza las fichas incompletas de las aulas anteriores. Incluye fabricante/modelo ficticios, serie patrimonial ficticia, unidad, clasificación orientativa, características, último y próximo mantenimiento, notas y estado. Docente y Biomédica pueden **editar las fichas y crear nuevos activos** (hasta 80 por aula). Todos pueden consultar las fichas.

Cada rol tiene un **registro libre de turno** (asunto, descripción y medición numérica opcional); Biomédica y Docente pueden vincularlo a un equipo. Queda guardado en SQLite y visible en Auditoría junto con autor, rol y fecha. **No introducir datos personales de pacientes reales, números de serie reales ni resultados de laboratorio reales.** Se generan nombres ficticios para los pacientes nuevos sin modificar los históricos.

El instalador v0.3.1 genera copia consistente de SQLite y del código y **conserva la imagen Docker anterior**. Si la actualización del contenedor o la verificación de salud falla, intenta restablecer el código y la imagen anteriores; el respaldo SQLite queda disponible para recuperación manual. No ejecuta `docker compose down -v`.

## Novedad v0.3.0 — Hospital híbrido

En cada aula el docente elige entre **1 y 6 áreas humanas**, con accesos rápidos para 2, 3, 4 o 6 estudiantes. Las áreas no seleccionadas son atendidas por **agentes virtuales** que ejecutan acciones en secuencia (ritmo configurable de 10, 15 o 30 segundos, más dispersión aleatoria). Los agentes no saltan dependencias: HIS admite antes de la recepción de Clínica; LIS informa antes de que Clínica reconozca el resultado, y así sucesivamente.

- Los agentes ejecutan exclusivamente las acciones permitidas de su departamento y se identifican como `AUTO · ...` en la auditoría CSV; los eventos incluyen `automated: true`.
- Los incidentes manuales siguen disponibles y los agentes virtuales trabajan incluso si el generador de incidentes está en **Manual** o **Pausado**. El modo **Automático** controla la generación de *nuevos incidentes*, no el personal virtual.
- Por seguridad didáctica, una estación asignada al agente virtual no admite nuevas sesiones de alumnos. Si el docente cambia el rol con alumnos ya conectados, estos no pueden ejecutar acciones hasta que se reactive el rol humano.
- Las aulas existentes mantienen los seis roles en modo **humano** hasta que el docente cambie expresamente la distribución. No se cambia ningún dato de pacientes ni de incidencias anteriores.
- Los agentes únicamente manipulan registros ficticios: ningún tratamiento ni decisión clínica real.

## Novedades principales

- Rediseño integral: tablero de operaciones, mapa de ocho servicios, inventario, pacientes, tareas, alarmas, incidentes y auditoría.
- **Seis roles:** HIS, Clínica, LIS, Biomédica, Farmacia e Imagenología. El docente puede operar todas las estaciones.
- **Tutorial emergente de cuatro pasos por rol** al ingresar por primera vez en la sesión; botón «Guía rápida» para abrirlo de nuevo.
- **Seis incidentes**: desaturación ficticia; falla de equipo; ingreso imprevisto; laboratorio prioritario; suministro pendiente; imagen pendiente.
- **Motor aleatorio** configurable por aula: apagado/manual (predeterminado), automático, pausado. Intervalos 30–900 s y dificultad inicial, intermedia e intensiva; se añade dispersión aleatoria al intervalo.
- **Colas de tareas interdependientes**, completadas solamente después de acciones verificables en las estaciones. Máximo cuatro incidentes abiertos por aula.
- Nuevos circuitos: ingreso → asignación de cama → recepción clínica; suministro → dispensación → recepción; estudio de imagen → informe → revisión clínica; LIS → resultado crítico → reconocimiento; reparación → coordinación clínica.
- Monitor visual ficticio, sin señales fisiológicas reales; WebSocket para actualización y refresco periódico como respaldo.
- Indicadores: ocupación, dispositivos operativos, incidentes abiertos y completados, tareas pendientes, tiempo medio de reconocimiento y órdenes LIS pendientes. Auditoría CSV para evaluación.
- **Compatibilidad de esquema de SQLite con v0.1**: nuevas tablas, sin borrar aulas antiguas. El nuevo esquema puede utilizarse sobre el volumen persistente existente; haz copia antes.

## Acceso y requisitos

Linux x86-64 o ARM64, Docker Engine, Docker Compose v2, una URL HTTPS publicada por proxy con soporte para WebSockets si se accede desde internet. Puerto local predeterminado `127.0.0.1:8765`. No expongas el servicio sin protección adicional.

**Primera instalación (nueva):**

```bash
bash scripts/preflight.sh
bash scripts/install.sh
# La instalación inicial muestra la contraseña docente una sola vez.
docker compose ps
```

**Actualización de v0.1 ya en el servidor:** consulta `docs/ACTUALIZAR_EN_DEVRES.md`. Antes de actualizar, guarda copia del volumen SQLite y del proyecto. Nunca ejecutes `docker compose down -v`.

## Cómo dirigir una sesión

1. El docente ingresa con su contraseña y crea un aula. Comparte **solo** el código del aula con los equipos.
2. Los equipos eligen el rol asignado y completan su tutorial emergente.
3. El docente activa un incidente manual para la demostración.
4. El grupo identifica las responsabilidades y ejecuta las acciones en las estaciones. El motor marca tareas completas al verificar las transiciones.
5. Para práctica libre, el docente activa modo automático y elige intervalo/dificultad. La pausa impide nuevos eventos automáticos, pero los incidentes existentes siguen abiertos.
6. Se analiza auditoría CSV, tiempos y coordinación. Un incidente «resuelto» significa **flujo didáctico completado**, no necesariamente recuperación de un paciente real.

## Seguridad y límites

- El código del aula no garantiza una identidad del participante. Los estudiantes seleccionan el rol en el ingreso; para exámenes de alta integridad se necesitaría autenticación institucional y asignación de roles del lado del servidor.
- Sesiones de 12 horas; contraseña docente fuerte en `.env`; nunca incluirla en Git, Drive o el ZIP.
- SQLite está configurado para **un solo worker** Uvicorn; el planificador automático también corre en ese único proceso. No escalar a múltiples réplicas sin implementar coordinación de tareas y base de datos centralizada.
- Las aulas previas quedan en `mode=manual` tras la migración. Ningún evento automático empieza sin orden docente.
- Los intervalos no son temporización clínica ni SLA. Las prioridades y valores de prueba son convenciones didácticas.
- Ni FHIR real, ni DICOM, ni HL7v2 certificados, ni control real de equipos, ni recomendaciones médicas.
- El servidor debe mantenerse bajo HTTPS/WS seguro, filtrado de acceso y copias programadas.

## Desarrollo

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt pytest httpx
ADMIN_PASSWORD=CLAVE_SOLO_PRUEBAS_2026 DATABASE_PATH=/tmp/hospital-test.db PYTHONPATH=. pytest -q
```

La aplicación se ejecuta con FastAPI y WebSockets; las interfaces usan JavaScript estándar sin dependencias externas de CDN. Los eventos se conservan en SQLite y los alumnos solo ven su aula.

**Seguridad de contenedor:** ejecución como usuario no privilegiado; se conserva el esquema de usuarios de la v0.1 para acceder al volumen SQLite.

**Licencia:** MIT; se conserva el texto del repositorio original.
