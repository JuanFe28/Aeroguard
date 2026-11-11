# AeroGuard — Resumen ejecutivo

Versión del documento: 10-11-2026 · Código: `1.2.0-rc.2` (en preparación) · Institución de origen: Unidades Tecnológicas de Santander (UTS), Bucaramanga, Colombia.

## Qué es

AeroGuard es una plataforma de software para **gestionar eventos de objetos aéreos no autorizados** (principalmente drones) sobre zonas que una organización necesita proteger. Reúne en una sola consola web lo que hoy suele estar disperso: las observaciones que entregan los sensores, las zonas restringidas, las alertas, la respuesta del operador y el registro auditable de lo ocurrido.

## Propósito

Dar a operadores de seguridad, laboratorios e integradores colombianos una herramienta propia, en español y bajo su control, para **ordenar la información y las decisiones humanas** ante la presencia de aeronaves no tripuladas, sin depender de plataformas extranjeras cerradas y costosas.

## El problema

- El uso de drones crece y con él los sobrevuelos no autorizados sobre aeropuertos, infraestructura crítica, instalaciones industriales, eventos y campus.
- Las soluciones comerciales existentes (Dedrone, DroneShield, Fortem, Aaronia) combinan hardware y software propietarios, se cotizan por proyecto y no tienen soporte local verificado en Colombia.
- Sin una consola que integre las fuentes, el operador revisa cada aviso a mano: una falsa alarma consume recursos y una omisión deja un incidente sin atender.
- En Colombia existe demanda institucional documentada: CODALTEC publicó en 2026 requerimientos de integración C-UAS y de prueba de concepto de radar para aeronaves no tripuladas ([detalle y fuentes](../auditoria-2026-10-21/03_INVESTIGACION_COMERCIAL.md)).

## La solución

| Capacidad | Qué hace |
|---|---|
| Ingesta de telemetría | Recibe paquetes de sensores registrados y los convierte en detecciones con trayectoria |
| Geocercas | Define zonas restringidas en el mapa y detecta invasiones con PostGIS |
| Alertas en tiempo real | Notifica por WebSocket, con sirena para eventos críticos; permite asignar y resolver con justificación |
| Reportes | Genera PDF, Excel y CSV con hash SHA-256 para verificar integridad |
| Auditoría | Registra las acciones en una cadena verificable criptográficamente |
| Roles | Administrador, operador y analista con permisos separados |
| Operación | Despliegue con Docker, métricas Prometheus, tableros Grafana, respaldo y restauración |

## Estado actual: comprobado, simulado y pendiente

| Comprobado con evidencia | Simulado o experimental | Pendiente |
|---|---|---|
| API, base de datos espacial, interfaz y roles funcionando | La telemetría proviene de un simulador o de pruebas | Integrar al menos un sensor o cámara real |
| 167 pruebas de backend y 11 de frontend aprobadas (10-11-2026) | La visión artificial usa heurísticas; el adaptador YOLO es opcional | Modelo de detección entrenado y evaluado con datos independientes |
| Candidata `1.2.0-rc.1` publicada e instalada en un servidor privado (28-10-2026) | El módulo de minería de datos usa 125.000 registros sintéticos | Entrevistas con usuarios y un piloto supervisado |
| Respaldo y restauración ensayados | Reglas del agente táctico marcadas como experimentales | Titularidad, licencia y forma jurídica del proyecto |

**Nivel de madurez tecnológica estimado: TRL 4** (componentes validados en laboratorio). El sustento está en [Madurez tecnológica](03_MADUREZ_TECNOLOGICA_TRL.md).

## Objetivo del siguiente periodo

Llevar AeroGuard de prototipo de laboratorio a **piloto supervisado en un entorno real (TRL 6)**: integrar una fuente de datos autorizada, validar la detección con un conjunto de prueba independiente y operar el sistema con un usuario real bajo revisión humana. Los objetivos específicos, el cronograma y los riesgos están en la [Propuesta del proyecto](02_PROPUESTA_PROYECTO.md).

## Qué diferencia a AeroGuard

- **Independiente del hardware:** se propone integrar los equipos que el cliente ya tiene, en lugar de vender un ecosistema cerrado.
- **Local y en español:** instalación en infraestructura del cliente, con los datos bajo su control.
- **Trazabilidad:** reportes con hash y auditoría encadenada, útiles como evidencia.
- **Transparencia:** cada afirmación del proyecto distingue lo comprobado de lo simulado; no se publican métricas de precisión que no se hayan medido.

Estas son ventajas por validar con usuarios, no ventajas demostradas en el mercado.

## Límites declarados

AeroGuard **no** neutraliza ni interfiere drones, **no** identifica pilotos y **no** ha sido probado con sensores físicos. Hoy es una herramienta de laboratorio y formación. Cualquier uso operativo requiere la validación descrita en la propuesta y el cumplimiento de la normativa aplicable ([matriz normativa](../auditoria-2026-10-21/04_DOCUMENTACION_Y_NORMATIVA.md)).

## Equipo

Proyecto desarrollado por estudiantes y el Laboratorio de Inteligencia Artificial de las UTS. Los nombres, roles y dedicación se completan en [Presupuesto y equipo](04_PRESUPUESTO_Y_EQUIPO.md).

## Dónde seguir

- Código y documentación: [repositorio en GitHub](https://github.com/JuanFe28/Aeroguard).
- Mapa completo de documentos: [docs/README.md](../README.md).
