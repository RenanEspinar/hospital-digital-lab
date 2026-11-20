# Arquitectura y modelo de información

```text
[Docente / estudiantes] -- HTTPS / WSS --> [Proxy TLS existente]
                                              |
                                              v
                                           127.0.0.1:8765
                                              |
                                              v
                                       [FastAPI + WebSockets]
                                       |      |       |
                                      HIS    LIS    Biomédica
                                              |
                                              v
                                         [SQLite]
                                         (volumen)
```

## Separación de responsabilidades

- HIS simulado: admisión y asignación de camas.
- Clínica simulada: órdenes y alarmas clínicas.
- LIS simulado: recepción de muestra y publicación de resultados.
- Ingeniería biomédica simulada: estado de equipos y alertas técnicas.
- Docente: aula, escenarios y auditoría.

## Mensajes didácticos

Cada acción produce un evento persistente y visible a participantes de la misma aula. Algunos eventos contienen objetos JSON inspirados en recursos HL7 FHIR:

- Admisión: **Encounter**, relacionado con un paciente sintético.
- Orden: **ServiceRequest**.
- Resultado de laboratorio: **Observation**.
- Estado de equipo: **Device**.

Los objetos **no son recursos FHIR completos ni perfiles nacionales validados**. No existe endpoint FHIR estándar, motor de terminología LOINC, catálogo SNOMED ni integrador HL7 v2 en esta versión. Su propósito es mostrar el flujo de información y la trazabilidad.

## Concurrencia

- La lógica de datos usa transacciones SQLite `BEGIN IMMEDIATE`, evitando asignaciones concurrentes de una misma cama.
- Un único proceso ASGI mantiene WebSockets de las salas.
- Si se usaran varios procesos, la propagación de eventos requeriría un servicio externo, por ejemplo Redis.
- Cada petición valida que el token corresponda al aula; el docente accede a sus aulas.

## Realismo clínico: límite deliberado

Los resultados y las alarmas **no reproducen una monitorización clínica real**, ni valores de alarma configurables por población. El objetivo es comprender interoperabilidad, gestión operativa y análisis de indicadores. Los mensajes, valores y tiempos pertenecen exclusivamente a una simulación.
