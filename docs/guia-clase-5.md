# Clase 5 — Simulación HIS/LIS y tablero operativo

**Asignatura:** Innovación, Sistemas de Información y Transformación Digital en la Gestión Biomédica.  
**Unidad 3, tema 3.1:** Indicadores estratégicos y tableros de control.  
**Duración sugerida:** 120 minutos.  
**Modalidad:** demostración docente + simulación multiusuario con equipos de estudiantes.

## Progresión académica

Las clases 3 y 4 abordaron HIS e interoperabilidad. **No volver a enseñar sus definiciones.** En esta clase se utilizan para obtener datos que alimentan indicadores.

La simulación no representa un hospital real ni reemplaza guías clínicas o normas de alarma. Se emplea para analizar el vínculo entre **eventos**, **tiempos de respuesta**, **disponibilidad** y **decisión gerencial**.

## Guion de la sesión

| Tiempo orientativo | Desarrollo |
| --- | --- |
| 0–15 min | Diferenciar dato, evento, indicador y objetivo. Mostrar el tablero vacío y establecer una línea base. |
| 15–35 min | Demostración del docente: paciente ficticio → admisión HIS → cama ocupada. Interpretar ocupación hospitalaria. |
| 35–55 min | Equipo clínica solicita analítica; LIS recibe muestra y publica resultado. Observar el indicador de órdenes pendientes. |
| 55–75 min | Escenario crítico ficticio: resultado de potasio predefinido → alarma → reconocimiento. Discutir tiempo de reacción y trazabilidad. |
| 75–95 min | Ingeniería biomédica registra una avería y luego recuperación. Medir disponibilidad de dispositivos. |
| 95–110 min | Exportación CSV; revisar errores de interpretación: disponibilidad ≠ utilización, reconocimiento ≠ resolución. |
| 110–120 min | Cierre y preguntas. Identificar qué métricas requieren datos temporales más detallados para ser válidas. |

## Roles

**Docente:** controla la sala y crea escenarios. **HIS:** admisiones. **Clínica:** órdenes y reconocimiento clínico. **LIS:** procesamiento simulado. **Biomédica:** equipos y averías.

## Preguntas para discutir

- ¿Por qué una ocupación del 85 % no demuestra por sí sola que el servicio sea eficiente?
- ¿Qué información se pierde si el LIS publica resultados sin asociarlos a la solicitud y al paciente?
- ¿Qué diferencia existe entre alarma generada, reconocida, investigada y resuelta?
- ¿Cómo cambia la disponibilidad de equipos si se reporta una avería no registrada anteriormente?
- ¿Qué denominador y qué periodo se usarían para comparar hospitales con capacidades distintas?

## Límites de los indicadores del prototipo

- **Ocupación:** camas ocupadas / camas simuladas. Corte transversal del aula; no mide estancia media.
- **Disponibilidad:** equipos operativos / inventario simulado. Es un estado instantáneo, no disponibilidad temporal bajo un SLA.
- **Alarmas activas:** conteo de alarmas sin reconocimiento; no representa prevalencia clínica.
- **Tiempo medio de reconocimiento:** promedio en segundos para alarmas reconocidas. No es tiempo de resolución ni resultado asistencial.
- **Órdenes pendientes:** solicitadas o recibidas sin resultado; no equivale a tiempo real de procesamiento.

Las reglas de interpretación anteriores son parte obligatoria del cierre docente.
