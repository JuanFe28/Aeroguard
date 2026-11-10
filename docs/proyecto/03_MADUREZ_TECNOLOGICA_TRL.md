# AeroGuard — Nivel de madurez tecnológica (TRL)

Versión: 10-11-2026. La mayoría de convocatorias de innovación pide declarar el nivel de madurez tecnológica (Technology Readiness Level, escala de 1 a 9) y sustentarlo. Este documento hace esa evaluación con evidencias del repositorio.

## Conclusión

**AeroGuard se ubica en TRL 4: tecnología validada en laboratorio.** La plataforma de software funciona de forma integrada y repetible, pero solo con datos simulados o de prueba. No alcanza TRL 5 porque ningún componente se ha validado con sensores reales ni en un entorno representativo del uso final.

La meta de la [propuesta](02_PROPUESTA_PROYECTO.md) es llegar a **TRL 6** en 12 meses.

## Evaluación nivel por nivel

| TRL | Definición | ¿Cumplido? | Evidencia o brecha |
|---|---|---|---|
| 1 | Principios básicos observados | Sí | Problema y contexto documentados en la [investigación comercial](../auditoria-2026-10-21/03_INVESTIGACION_COMERCIAL.md) |
| 2 | Concepto tecnológico formulado | Sí | Historias de usuario, criterios de aceptación y arquitectura en la [planificación](../PLANIFICACION_V1.1.md) |
| 3 | Prueba de concepto | Sí | API, interfaz, geocercas y alertas funcionando desde la versión 1.1.0 |
| 4 | Validación de componentes en laboratorio | Sí | Sistema integrado con PostgreSQL/PostGIS y RabbitMQ; 167 pruebas de backend y 11 de frontend aprobadas el 10-11-2026; 51 casos de navegador; pruebas de carga WebSocket con 10, 50 y 100 clientes; instalación en servidor privado el 28-10-2026 ([QA](../qa-2026-10-29/README.md), [despliegue](../../deploy/RESULTADO_2026_10_28.md)) |
| 5 | Validación en entorno relevante | **No** | Falta integrar una fuente real (cámara o sensor) y validar el flujo completo con datos reales |
| 6 | Demostración en entorno relevante | No | Falta un piloto supervisado con un usuario real y un modelo de detección evaluado |
| 7 | Demostración en entorno operativo | No | — |
| 8 | Sistema completo y certificado | No | — |
| 9 | Sistema probado en operación | No | — |

## Madurez por componente

No todos los componentes están en el mismo punto. Esta tabla evita presentar el conjunto como más maduro de lo que es.

| Componente | Madurez | Comentario |
|---|---|---|
| API, autenticación y roles | TRL 4, alto | Probado con usuarios persistidos, revocación de sesión y límites de intentos |
| Motor geoespacial y geocercas | TRL 4, alto | PostGIS con índice espacial; verificado en PostgreSQL y SQLite |
| Alertas en tiempo real | TRL 4, alto | WebSocket probado bajo carga local |
| Reportes y auditoría | TRL 4, alto | Archivos con hash verificable y cadena de auditoría |
| Despliegue y operación | TRL 4, alto | Imágenes publicadas, instalación privada, respaldo y restauración ensayados; monitoreo solo verificado en local |
| Ingesta de sensores | TRL 3 | Solo simulador y pruebas; sin equipo físico |
| Visión artificial | TRL 3 | Heurísticas con OpenCV; adaptador YOLO opcional; sin conjunto de prueba independiente ni métricas |
| Agente táctico y automatización | TRL 3 | Reglas locales experimentales; integración externa sin probar |
| Minería de datos | TRL 2–3 | Ejercicio académico con datos sintéticos; sus métricas no describen el desempeño real |

## Ruta al siguiente nivel

| Para alcanzar | Hace falta | Evidencia que lo demostrará |
|---|---|---|
| TRL 5 | Integrar una fuente real autorizada; publicar e instalar la candidata `1.2.0-rc.2`; monitoreo activo en el servidor | Registro de telemetría real, informe de integración y evidencia del servidor |
| TRL 6 | Modelo de detección evaluado en prueba ciega; piloto supervisado con un aliado | Informe de ensayo con métricas por escenario y acta del piloto |
| TRL 7 | Operación continua en el sitio del usuario con soporte | Contrato o convenio, registro de incidentes y disponibilidad medida |

## Cómo usar este documento en un formulario

- **Declarar:** «TRL 4 al inicio; TRL 6 al finalizar».
- **Sustentar:** citar las pruebas automatizadas, la candidata publicada y la instalación en servidor, con los enlaces de esta página.
- **No afirmar:** que el sistema detecta drones en campo, que tiene una precisión determinada o que ha operado con sensores reales.
