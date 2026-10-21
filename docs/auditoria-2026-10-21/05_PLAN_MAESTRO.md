# Informe 5 — Plan maestro de evolución

Fecha base: 21-10-2026. Estimaciones orientativas de esfuerzo, no plazos prometidos: equipo pequeño con disponibilidad parcial y acceso a los recursos necesarios. Asignar responsables reales antes de comprometer fechas. El Release académico y la aptitud comercial tienen puertas de aceptación diferentes.

## Camino académico

TEST → RELEASE → ENTREGA Y DEMOSTRACIÓN FINAL

| Etapa / horizonte | Objetivo y actividades | Dependencias / prioridad / complejidad | Riesgo | Aceptación, evidencia y entregable |
|---|---|---|---|---|
| Revisión de TEST, ahora | Revisar 64 históricas, 15 casos nuevos, 3 cargas y alcance de Selenium | Hecho localmente; P0, baja para revisión | Confundir cobertura con detección real | XML/JSON y capturas en auditoría; 79 funcionales + 3 carga, límites expresos |
| Preparación Release, 2–5 jornadas orientativas | Triaje de dependencias, aprobar SemVer, revisar changelog, contratos de candidata y notas | Rúbrica docente y disponibilidad del equipo; P0, media | Cambios incompatibles al actualizar librerías | Criterios aceptados, dependencias resueltas o excepción académica explícita; notas revisadas |
| Construcción y ensayo, 2–4 jornadas tras disponer de Docker | Construir cuatro imágenes, probar backend test-stage, stack PostgreSQL, persistencia y restauración | Motor Docker y recursos; P0, media | Incompatibilidad SQL/ORM, credenciales demo, worker incompleto | Build y arranque documentados, digests, smoke con datos de prueba, recuperación medida |
| Publicación académica, después de aceptación | Elegir registro, publicar digests autorizados, pull limpio, candidata etiquetada | Autorización explícita; P0 para RELEASE-02, media | Publicación prematura o imágenes distintas de las probadas | Registro y manifiesto comprobados, changelog y notas corresponden al commit |
| Entrega y demostración | Ensayar recorrido, declarar simulaciones, presentar resultados y pendientes | Release aceptado y acceso a mapas/red; P0, baja | Falta de Internet o mezcla de datos demo/reales | Un tercero reproduce demo; rúbrica y acta de aceptación; paquete de evidencias |

No cerrar RELEASE-02 por haber escrito un workflow. DEPLOY-01/02, OPERATE-01/02 y MONITOR-01/02/03 conservan su trazabilidad en Trello y deben acordarse si el docente los exige para la entrega.

## Camino comercial

AUDITORÍA → VALIDACIÓN DEL PROBLEMA → DEFINICIÓN DEL MVP → VALIDACIÓN TÉCNICA REAL → PILOTO → PREPARACIÓN COMERCIAL → LANZAMIENTO

| Etapa / horizonte orientativo | Objetivo y actividades concretas | Dependencias / prioridad / complejidad | Riesgos | Criterio de avance y evidencias |
|---|---|---|---|---|
| Auditoría, ahora | Revisar brechas, fuentes y límites; conservar cambios existentes | Código y evidencias; P0, media | Tratar prototipo como sistema de seguridad | Informes 1–4 revisados; riesgos y decisiones con responsables |
| Problema, semanas 1–3 | 8–12 entrevistas propuestas; observar trabajo actual, equipos y compra; elegir segmento | Acceso voluntario a operadores/compradores; P0, media | Opiniones sin necesidad o presupuesto | Problema repetido con ejemplos, costo/tiempo medido y patrocinador identificable; registro anonimizado |
| MVP, semanas 3–5 si hay demanda | Delimitar un sitio, una fuente y un flujo de verificación humana; especificar qué no se ofrece | Problema validado, titularidad y acceso a datos; P0, media | Añadir funciones sin uso ni datos | PRD, contrato de API, criterios negociados y decisión de continuar o detener |
| Validación técnica, 1–3 meses según acceso | Integrar fuente autorizada; reparar contratos, sesiones y persistencia; medir capacidad. Si incluye visión: dataset, modelo específico y ensayo ciego | Equipos, permisos, anotación, hardware y derechos; P0, alta | Falta de clases/escenarios, fuga train-test, falsos avisos | Informe de ensayo repetible con resultados y errores por escenario; ninguna métrica inventada |
| Piloto, 1–2 meses después | Operación supervisada, doble verificación, métricas del flujo y soporte | Criterios técnicos logrados, contrato y privacidad; P0, alta | Uso fuera de alcance o responsabilidad ante omisiones | Acta del cliente, incidentes revisados, costo real de soporte y decisión comercial |
| Preparación comercial, condicionada al piloto | Costos/precios, contratos, licencias, SBOM, actualizaciones, backup y respuesta a incidentes | Piloto útil y derechos claros; P1, alta | Margen insuficiente o dependencia de proveedor | Unidad económica justificable, soporte ensayado, aceptación de riesgos y oferta firmable |
| Lanzamiento limitado y luego expansión | Primeros contratos en un alcance probado; revisión por país para Latinoamérica | Recursos financieros y capacidad de servicio; P2, alta | Vender más de lo que se puede operar | Renovación/uso demostrable, calidad sostenida y repetición del piloto; sin cuota ni ingresos supuestos |

El calendario comercial puede detenerse si no hay problema validado, acceso a equipos o base legal. No se fija una fecha de venta. Internacionalización requiere análisis local; Colombia no otorga acceso automático a otros mercados.

## Backlog priorizado por necesidad

| Prioridad | Mejora | Motivo comprobado | Aceptación / dependencia |
|---|---|---|---|
| P0 inmediato | Resolver avisos de dependencias en lotes compatibles | 65 avisos del entorno; 54 en 8 dependencias que forman parte del runtime instalado y 11 en herramientas | Triaje con alcance/exposición, parche o decisión escrita; regresiones después de cada lote |
| P0 antes de uso público | Bootstrap sin cuentas conocidas, secretos obligatorios, readiness y BD sin fallback silencioso | Credenciales semilla, defaults y health positivos ante error | Pruebas de arranque fallido/seguro, configuración y recuperación |
| P0 para fuente real | Autenticación de sensor/servicio, origen y clasificación de datos | Ingesta recibe packet sin asociar sensor y antes inventaba inferencia | Rechazar fuente inválida, conservar identidad/unidades y evidencia; no confirmar dron sin análisis |
| P1 para MVP integrado | Contratos cliente/API, login según modo y eliminación de mocks de rutas reales | Diferencias de método/cuerpo/endpoints y pantallas estáticas | Pruebas de contrato y E2E sobre backend con roles reales |
| P1 para reportes operativos | Dataset de BD, filtros, formatos e ID de archivo persistido | Exportaciones actuales sintéticas y descarga recompilada | Archivo corresponde al período y registros, inexistente devuelve 404, recuperación idéntica |
| P1 antes de piloto | XSS, reset/session, límites y rate limits | Interpolación HTML y tokens/reset sin revocación | Pruebas de entrada maliciosa, agotamiento y cierre de sesión efectivo |
| P1 para operación | Auditoría concurrente, backup, monitorización y retención | Hash sin anclaje externo, estado local y métricas ausentes | Ensayos de concurrencia/recuperación y alertas sobre fallos reales |
| Solo tras decisión de producto | Modelo visual especializado | Ningún modelo/dataset/métrica de campo acreditado | Ensayo por escenario y tasa de falsos avisos; sin umbral universal inventado |
| Aplazable | Fusión multisensor, tracking avanzado y escalado distribuido | Dependen del hardware y uso que seleccione el piloto | Caso medido que justifique complejidad y presupuesto |
| Fuera del alcance actual | Neutralización / interferencia / atribución de intención | No existen capacidades ni autorización acreditadas | No desarrollar como extensión libre del dashboard |

## Protocolo de validación real propuesto

Definir primero la tarea: detectar un objeto visual no es conocer coordenadas geográficas ni identidad del piloto. Seleccionar cámaras y distancias, día/noche/clima, tamaños y distractores (aves, aeronaves, objetos urbanos). Documentar consentimiento, licencia y retención. Separar entrenamiento/evaluación por vuelo/sitio/fecha para evitar fuga. Congelar modelo, configuración, hardware y versión; evaluar un conjunto ciego con ground truth y publicar errores.

Medir precisión/recall, mAP si procede, falsos avisos por hora, omisiones, latencia total P50/P95, recursos y condiciones de fallos. Acordar umbrales con el usuario y consecuencias del error antes del ensayo; no fijar un 95 % por conveniencia. Mantener revisión humana y prohibir acciones automáticas sobre terceros. Sin pesos/datos y estos resultados, no declarar validada la detección.

## Próximo hito recomendado

**Candidata académica revisada y reproducible**, con triaje de dependencias, build y prueba de imágenes, rúbrica acordada, notas honestas y publicación autorizada. En paralelo, completar entrevistas y conseguir un escenario de integración real. Esos dos hitos deciden qué programar después; la cantidad de funciones añadidas no es la medida de avance.
