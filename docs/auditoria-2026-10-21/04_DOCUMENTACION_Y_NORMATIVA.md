# Informe 4 — Documentación necesaria y pertinencia normativa

Fecha de revisión: 21-10-2026. Las prioridades son propuestas de gestión. **O-C** = obligación condicionada a la actividad/datos reales; **R** = recomendación profesional; **F** = futura y condicionada a una decisión de producto. La rúbrica académica y los acuerdos de propiedad no fueron aportados.

## A. Documentación técnica

| Documento | Estado encontrado | Acción / criterio de terminación | Prioridad / clase |
|---|---|---|---|
| README e instalación | Existente, con afirmaciones y rutas desactualizadas | Actualizado con alcance demo y enlace a auditoría; validar instalación limpia | P0 / R |
| Arquitectura y flujo de datos | README y PLANIFICACION_V1.1 | Separar diseño previsto de flujo ejecutado; mapa de componentes y dependencias en informe 1 | P0 / R |
| Requisitos / aceptación | Historias y Gherkin en planificación; RF en README | Completar trazabilidad requisito → código → prueba → límite; aceptar criterios docentes | P0 / R académica |
| API / Postman | Exportaciones y colecciones existentes | OpenAPI actual guardado; detectar diferencias de contrato y ejecutar colección en entorno limpio | P1 / R |
| Modelo de datos y migraciones | SQLAlchemy + init.sql | ERD, diccionario/unidades, estrategia de migraciones y compatibilidad PostgreSQL/SQLite | P1 / R |
| Pruebas y evidencias | TEST histórico y auditoría nueva | Conservar ejecuciones, commit, parámetros y entornos; evitar llamar IA validada a sintéticos | P0 / R |
| Seguridad y dependencias | TEST-03 y escaneo actual | Modelo de amenazas, triaje de 65 avisos, gestión de secretos, sesiones e identidad de sensores | P0 / R y obligaciones según datos |
| Inventario / SBOM / licencias | Requirements y freeze; sin SBOM por imagen | Inventario de runtime, dependencias, licencias y pesos; no mezclar herramientas de test con producto | P0 comercial / R |
| Release y changelog | Preparados en esta auditoría | Política aceptada, manifiesto y candidata probada; publicación sigue pendiente | P0 / R y tarjetas RELEASE |
| Operación / backup / rollback | Guía 07 propuesta | Ensayos de restauración y reversión con evidencia, responsables y objetivos acordados | P1 / R |
| Observabilidad y capacidad | Pruebas WS locales; sin guía operativa completa | Definir métricas, readiness, retención, alertas y prueba prolongada | P1 / R |

`docs/GUIA_EXPOSICION_LUNES.md` sigue siendo histórica: menciona 41 pruebas y un BAT eliminado antes de esta tarea. Usar la guía nueva para esta candidata. No se borraron evidencias ni se reescribieron ZIP antiguos.

## B. Documentación de producto

| Documento | Estado / alcance | Próxima acción | Prioridad |
|---|---|---|---|
| Ficha técnica honesta | Parcial, ahora descrita en informes 1 y 3 | Consolidar fuentes de datos, modo demo, detección experimental y funciones excluidas | P0 |
| Definición de MVP y usuario objetivo | Hipótesis, no validada | Elegir un usuario, un problema, una fuente real y medidas de éxito | P0 |
| Manual de usuario | Guía académica disponible | Completar roles, recuperación, errores, acciones permitidas y límites de alertas | P1 |
| Especificación de rendimiento de detección | Ausente | Dataset, escenarios, métricas, hardware y umbrales acordados antes de prometer precisión | P0 para vender detección |
| Gestión de versiones y compatibilidad | Política propuesta | Declarar contratos soportados, actualizaciones y fin de soporte | P1 |
| Roadmap / aceptación de piloto | Informe 5 | Negociar con un usuario real; registrar decisión de continuar o detener | P0 |

## C. Documentación empresarial

| Documento | Estado | Uso / siguiente decisión | Prioridad / clase |
|---|---|---|---|
| Lean Canvas / modelo de negocio | Hipótesis en estudio comercial | Problema, segmentos, propuesta, canal, ingresos, costos y métricas; validar con entrevistas | P1 / R |
| Costos y precios | Sin mediciones ni cotizaciones | Medir infraestructura y soporte; incluir hardware e integración, separar costos iniciales/recurrentes | P0 antes de oferta / R |
| Acuerdo entre integrantes y titularidad | No encontrado | Determinar autores, aportes, derechos patrimoniales y reglas de la institución | P0 comercial / R y revisión jurídica |
| Licencia del código propio | README: uso educativo; package: UNLICENSED; sin licencia comercial encontrada | No presumir derecho a relicenciar o vender. Acordar con titulares | P0 comercial / O-C |
| Licencias de terceros / datos / modelo | No consolidadas | Revisar obligaciones de cada componente y dataset antes de distribución | P0 comercial / O-C |
| Contrato de piloto | Ausente | Alcance, responsabilidades, datos, soporte, criterios de éxito, salida y eliminación de datos | P0 para piloto / R |
| Términos, SLA, soporte y responsabilidad | Ausentes | Horarios, escalamiento, respuesta, mantenimiento, límites medibles y fallos de detección | P1 / R; obligaciones según contrato |
| Identidad empresarial / facturación / impuestos | No verificada | Elegir forma de operación y revisar trámites con contador/asesor; no inferir estado empresarial del repositorio | Antes de vender / F |
| Marca y registro de software | No verificados | Revisar antecedentes de marca; registro de software como evidencia de autoría si procede | P2 / R |

La [DNDA explica que el registro es declarativo y no obligatorio](https://www.derechodeautor.gov.co/es/otros/software). No sustituye los acuerdos de cesión/titularidad. Si se incorpora Ultralytics, revisar [sus términos AGPL/Enterprise](https://www.ultralytics.com/license) y los derechos de los pesos/datos; el adaptador actual no prueba que exista una licencia comercial ni que el modelo esté incluido.

## D. Colombia: aplicabilidad normativa

Esta matriz distingue lo verificado en fuentes oficiales de lo que depende del despliegue. No es una certificación de cumplimiento ni una conclusión de que todas las filas apliquen hoy. Fuentes y limitaciones de acceso en el informe 06.

| Tema | Cuándo aplica / evidencia oficial | Documento o control necesario | Clasificación y límite |
|---|---|---|---|
| Datos personales | Si usuarios, imágenes o registros permiten identificar personas. [Ley 1581 de 2012](https://www1.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981) | Roles responsable/encargado, finalidades, base de tratamiento, políticas, atención de derechos y seguridad | O-C. Revisar excepciones y reglamentación consolidada; no afirmar obligación universal de RNBD |
| Videovigilancia | La SIC considera tratamiento la captación, transmisión y conservación de imágenes identificables. [Concepto SIC](https://sedeelectronica.sic.gov.co/publicaciones/boletin-juridico/concepto/tratamiento-de-datos-personales-traves-de-camaras-de-videovigilancia) | Avisos, minimización, accesos, retención/borrado y reglas de grabación; no captar más de lo necesario | O-C si hay datos personales; no toda imagen de un objeto aislado identifica una persona |
| Servicios externos | Si se envían imágenes/telemetría personal a n8n, mensajería, LLM o nube | Inventario de destinos, contrato de tratamiento, permisos y evaluación de transferencias/transmisiones | O-C según datos, países y actores. Workflow en un archivo no acredita cumplimiento |
| Operación de aeronaves | Si se realizan vuelos de prueba o se ofrece operación UAS. [Normativa Aerocivil](https://www.aerocivil.gov.co/normatividad) | Plan de pruebas con operador autorizado según categoría y lugar; consultar RAC vigente y restricciones oficiales | O-C para operación de drones. Un dashboard por sí solo no convierte a su proveedor en explotador aéreo |
| Zonas y umbrales | La regulación y áreas publicadas por autoridad son distintas de polígonos de ejemplo. [Información UAS](https://www.aerocivil.gov.co/prensa/noticias/Pages/Informacion-importante-sobre-la-regulacion-de-la-aviacion-no-tripulada-UAS.aspx) | Registrar fuente/fecha y alcance de cada zona; coordinar tecnologías antidrones según contexto | No tratar 120 m configurados ni zonas semilla como dictamen jurídico o cartografía oficial |
| RF e interferencia | Solo si se incorporan equipos o funciones de espectro. [Resolución MinTIC 2774/2013](https://normograma.mintic.gov.co/mintic/compilacion/docs/resolucion_mintic_2774_2013.htm) | Evaluación de equipo, uso y autorización correspondiente; coordinación con autoridades competentes | O-C. AeroGuard no tiene hardware RF ni neutralización demostrados; no habilitarlos por una recomendación de software |
| Software y propiedad intelectual | Código, modelos, imágenes y aportes de terceros | Cadena de derechos, licencia de distribución y obligaciones de dependencias | O-C según uso y contratos. No asumir que un repo público concede licencia comercial |
| Seguridad de la información | Deberes asociados al tratamiento y compromisos del cliente | Control de acceso, gestión de incidentes, parches, respaldo y trazabilidad | Obligaciones según contexto; ISO 27001 u OWASP son referencias, no certificaciones obtenidas ni requisitos universales |
| Prestación de vigilancia privada | Si el negocio presta servicios de vigilancia, además de proveer software | Revisar actividades y eventual régimen sectorial con asesor y autoridad | Asunto jurídico por determinar; vender una licencia no demuestra por sí solo que se opere un servicio vigilado |
| Responsabilidad por decisiones | Según oferta, contrato, datos y uso del cliente | Limitaciones claras, revisión humana, procedimiento ante fallo y pruebas de aceptación | Revisión jurídica antes de piloto. Un descargo comercial no sustituye el funcionamiento ni elimina obligaciones |

## Orden de elaboración

Antes de la entrega: aceptar alcance y versiones, terminar evidencias y resolver dependencias/contenedores. Antes de un piloto: identidad/origen de sensores, contrato, privacidad, seguridad, backup restaurado y ficha técnica. Antes de vender: titularidad/licencias, costos, soporte y aceptación operativa. Certificaciones y expansión regulatoria internacional se evaluarán después de demostrar demanda y viabilidad técnica; no son funcionalidades que deban agregarse por intuición.
