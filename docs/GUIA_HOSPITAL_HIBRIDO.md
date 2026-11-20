# Hospital Digital Lab v0.3.1 — Guía del docente (3 o 4 estudiantes)

## Cómo configurar el personal híbrido

1. Ingresa como **Docente** y selecciona el aula. Para hacer ensayos sin afectar una clase, crea una **aula nueva de prueba**.
2. En **Personal humano y agentes virtuales**, pulsa **3 estudiantes** o **4 estudiantes**, o marca manualmente las áreas que quieres entregar a los alumnos.
3. Revisa el listado. **Marcado = estudiante humano**; **sin marcar = agente virtual**.
4. Selecciona el **ritmo virtual** (rápido ~10 s, normal ~15 s o pausado ~30 s) y pulsa **Guardar distribución**. Hay dispersión en cada turno; no significa que los agentes respondan en una fecha clínica exacta.
5. Comparte el código del aula. Cada alumno ingresa con su rol humano. Las áreas automáticas rechazan nuevas sesiones humanas para evitar dobles intervenciones.
6. Mantén el **motor de incidentes en Manual** para comenzar con un caso. Después puedes activar **Automático** para generar nuevos incidentes.

**Importante:** el modo **Pausado** detiene la creación automática de incidentes, pero los **agentes virtuales continúan atendiendo los casos pendientes**. Para detener agentes virtuales, asigna temporalmente sus roles a estudiantes mediante la configuración del personal.

## Presets recomendados

| Estudiantes | Roles humanos | Roles virtuales |
| --- | --- | --- |
| 2 (prueba) | Clínica, LIS | HIS, Biomédica, Farmacia, Imagenología |
| 3 | Clínica, Biomédica, LIS | HIS, Farmacia, Imagenología |
| 4 | HIS, Clínica, LIS, Biomédica | Farmacia, Imagenología |
| 6 | Los seis roles | Ninguno |

Se pueden cambiar manualmente los roles, también con más alumnos por departamento. La asignación determina **áreas** atendidas por alumnos, no número de cuentas ni número máximo de estudiantes.

## Estudiantes conectados y suplencia automática

En **Estudiantes conectados y sustitución**, el docente ve los seis departamentos, sus estudiantes activos o sin actividad, y un botón por rol para tomar o devolver el control. Las sesiones se consideran activas si reportan actividad en los últimos 45 segundos. No confundir «sin actividad» con una desconexión de red confirmada; una pestaña suspendida también puede perder el latido.

La opción «Cubrir ausencias automáticamente (60 s)» está desactivada inicialmente. Cuando se habilita, un rol asignado a humanos pero sin actividad puede pasar a **suplencia** después de 60 segundos. El regreso del estudiante restaura el modo humano. Los **bots permanentes** solo cambian cuando el docente los reasigna. En el registro CSV quedan documentados la cobertura, su cierre y las acciones del bot.

## Inventario biomédico y registros libres

**Equipamiento** → **Ver ficha**. Docente/Biomédica pueden editar marca y modelo ficticios, identificación, número de serie sintético, fechas de mantenimiento, características, observaciones y dar de alta otros activos. Cada estudiante también puede ingresar notas y mediciones sintéticas en **Registro libre de mi turno**, con atribución y unidad. Biomédica puede escoger un activo relacionado.

No cargar datos identificables ni clínicos reales: el software simula un hospital, no realiza metrología certificada ni toma decisiones médicas.

## Ejercicio guiado (3 alumnos, 15–20 minutos)

1. Configura tres roles humanos (Clínica, Biomédica, LIS), motor **Manual**, ritmo virtual **10 s**.
2. **Docente:** pulsa **Suministro pendiente**.
3. **Sistema:** crea una orden para Farmacia (virtual) y una tarea dependiente de Clínica (humana).
4. **Agente de Farmacia:** dispensa el insumo ficticio al llegar su turno; aparece `AUTO · Farmacia` en Auditoría.
5. **Estudiante de Clínica:** confirma la recepción en su estación. El incidente cambia a completado.
6. **Docente:** pulsa **Imagen urgente**. El agente de Imagenología informa el examen; Clínica revisa el informe.
7. **Docente:** pulsa **Falla de equipo**. Biomédica humana registra la restauración técnica; Clínica reconoce la alarma. Después pulsa **Laboratorio crítico**: LIS informa el resultado y Clínica reconoce la alerta.
8. **Docente:** exporta la bitácora CSV y revisa `actor`, `role`, `type`, `payload`, tiempos y responsabilidades.

## Evaluación y límites

- Un incidente **completado** significa **flujo de simulación completado**, no atención médica ni resolución clínica validada.
- En la bitácora las acciones virtuales se identifican por el actor `AUTO · ...` y `automated:true` en `payload`.
- Una tarea humana no se completa por agentes de otras áreas.
- Si cambias un rol que ya tenía alumnos conectados a **automático**, esos alumnos no pueden continuar ejecutando acciones en esa estación. Evita cambiar de asignación durante una evaluación.
- Los agentes procesan una acción por turno, no órdenes clínicas reales. No conectan ningún equipo ni acceden a pacientes reales.
- Las aulas creadas en v0.2.2 conservan los seis roles **humanos** hasta que el docente los configure.
