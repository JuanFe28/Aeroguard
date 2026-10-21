# Informe 2 — Diagnóstico de RELEASE

Fecha: 21-10-2026. **Estado: preparada parcialmente; cierre académico y publicación pendientes.**

## Alcance académico encontrado

La exportación de Trello contiene exactamente dos tarjetas activas de Release, ambas sin descripción, sin fecha límite y sin criterios de aceptación, marcadas `dueComplete=false`:

1. [RELEASE-01 — Definir estrategia de versionado SemVer y generar CHANGELOG.md](https://trello.com/c/9x67PgRt).
2. [RELEASE-02 — Publicar imágenes de contenedores en GitHub Container Registry (GHCR) o Docker Hub](https://trello.com/c/EzGK1g5I).

**Los enlaces autoritativos y títulos íntegros son los de `evidencias/trello-alcance.json`.** La rúbrica docente no está disponible. Los criterios de la matriz siguiente son propuestas profesionales complementarias, no requisitos académicos inventados. Las tareas DEPLOY, OPERATE y MONITOR siguen separadas: su presencia en el tablero no las convierte automáticamente en criterios de RELEASE.

## Matriz de cierre

| Tarea | Estado real | Evidencia | Problema / acción | Criterio propuesto de aceptación |
|---|---|---|---|---|
| RELEASE-01: SemVer | Política redactada; pendiente aceptación | Política de este informe; `pyproject.toml`, `package.json`, `.env.example` ya decían 1.1.0 | No hay tags ni API pública estable declarada; confirmar numeración antes de etiquetar | Política aprobada, versiones coherentes, commit de candidata identificado y decisiones registradas |
| RELEASE-01: CHANGELOG | Archivo preparado localmente | `CHANGELOG.md`, dos commits inspeccionados | Revisar y versionar junto al paquete; todavía no hay publicación | Cambios, correcciones y limitaciones trazables al código; sin atribuir funcionalidades inexistentes |
| RELEASE-02: imágenes | No completada | Cuatro Dockerfiles y workflow manual preparado | Motor Docker ausente; construir, ejecutar y escanear cada imagen | Cuatro imágenes construidas y probadas, tag exacto, digest y lista de componentes conservados |
| RELEASE-02: registro | Pendiente de ejecución y autorización | Workflow no contiene push; guía de publicación propuesta abajo | Elegir GHCR o Docker Hub y política de acceso; no se usaron credenciales de registro | Pull desde entorno limpio por digest y coincidencia con manifiesto aprobado |
| Pruebas de candidata | Aprobadas para alcance local | 79 funcionales + 3 carga + Selenium + sintaxis | No cubren PostgreSQL, broker, n8n ni reconocimiento de campo | Repetir desde commit acordado y conservar XML/JSON, versiones del entorno y resultados |
| Dependencias | Bloqueo abierto | `baseline/dependencias.json`: 65 avisos / 11 paquetes | Triaje por componente y versión; actualización incremental con regresiones | Remediación o aceptación explícita, acotada y documentada para la demo; no aceptación automática para uso público |
| Documentación / demo | Preparadas y verificadas parcialmente | Índice, guía, notas, capturas, OpenAPI actual | Revisar con docente; aplicar límites de datos sintéticos | Un tercero reproduce la demo con credenciales demo y distingue API de frontend simulado |
| Instalación contenedorizada | Revisión estática hecha | `compose-config.txt`, Dockerfile corregido | Falta validar arranque, BD, persistencia y reconstrucción | Stack en entorno aislado, readiness comprobado, reinicio sin pérdida y artefactos por digest |
| Respaldo / reversión | Procedimiento propuesto | Guía 07 | No se ejecutó restauración ni rollback | Ensayo con datos de prueba, hashes y tiempo de recuperación registrados |
| Aprobación académica | Pendiente | No hay rúbrica aportada | Contrastar alcance y excepciones con docente | Acta/aceptación sobre evidencias y limitaciones de esta candidata |

No se ha marcado ninguna tarjeta como terminada ni se ha escrito en Trello.

## Política de versiones propuesta

Referencia: [SemVer 2.0.0](https://semver.org/lang/es/), consultada el 21-10-2026.

- Mantener `1.1.0` como identificación interna existente; se corrigió el valor predeterminado de FastAPI que todavía decía `1.0.0`. Esto no crea una versión oficial.
- Usar `MAJOR.MINOR.PATCH`: MAJOR para incompatibilidad de contratos acordados, MINOR para funciones compatibles, PATCH para correcciones compatibles. Declarar primero qué API se promete mantener.
- La siguiente candidata podría denominarse **`v1.1.1-rc.1`**, si el equipo acepta estas correcciones como parche. Es una propuesta: **no se cambió a ese número ni se creó tag**. Si se redefine el contrato de ingesta/integración, reconsiderar MINOR o MAJOR según compatibilidad.
- Cada candidata apunta a un commit revisado, con evidencias y manifiesto de imágenes. Incrementar `rc.N` cuando cambie su contenido; no reemplazar tags publicados.
- Publicar `vX.Y.Z` solo después de aprobar los criterios y obtener autorización. Una versión académica aprobada sigue etiquetada como prototipo, sin promesas de detección validada.

## Correcciones preparadas en este árbol

- Génesis de auditoría consistente; test de alteración de registros.
- Autenticación y permisos en telemetría, lectura/escritura de dictamen y disparo de incidente. Integraciones n8n/simulador deberán enviar Bearer válido; no se provisionó token.
- Identificación fiel de OpenCV/Pillow/demo, filtrado explícito de clases YOLO, rechazo de bytes corruptos y límites de imagen.
- Telemetría sin inferencia visual no declara una confirmación de dron ni confianza inventada.
- Reportes indican dataset sintético; demo y recomendaciones locales no sugieren neutralización.
- Dockerfile del backend incluye requisitos de test y detector desde contexto raíz, OpenMP y configuración pytest; ejecución con un worker por el estado en memoria. Persistencia de reportes alineada con el volumen de Compose.
- Verificador `scripts/release_checks.py` y CI con SAST y revisión de dependencias. El CI de dependencias fallará mientras los avisos sigan abiertos: no está falsamente verde.
- Workflow manual de construcción de cuatro imágenes y conservación de artefactos; sin permisos de escritura de paquetes ni comandos de publicación.

Los cambios de Docker y GitHub Actions están preparados, pero no se presentan como construidos ni ejecutados en GitHub. Antes de publicar conviene fijar las acciones a SHA verificado, fijar dependencias transitivas y generar SBOM de cada imagen.

## Orden concreto de ejecución

1. Revisar este diagnóstico y el diff conservando los dos archivos eliminados previamente. No mezclar esos borrados con una decisión de Release sin aclarar su intención.
2. Resolver el triaje de dependencias: separar runtime, herramientas y componentes no usados; actualizar en lotes compatibles y volver a medir. Starlette está limitado por la versión de FastAPI y requiere una actualización coordinada; no basta elevar solo la transitiva.
3. Aprobar alcance académico: demo sintética, API SQLite y límites expresos. Si se exige detector entrenado o reportes de BD, esas capacidades siguen pendientes y el Release debe esperar.
4. Encender Docker en el entorno autorizado y ejecutar los builds y pruebas de la guía. Corregir cualquier fallo antes de distribuir imágenes.
5. Comprobar PostgreSQL, persistencia, login, permisos, ingesta autenticada y exportaciones; aclarar que PostGIS y RabbitMQ no están integrados de extremo a extremo.
6. Ejecutar verificador desde el commit de candidata, recorrido Edge y ensayo de respaldo/restauración. Adjuntar evidencias a la entrega local.
7. Aceptar número de candidata, notas y manifiesto. Solicitar autorización para la publicación concreta en el registro elegido.
8. Publicar únicamente los digests aprobados; verificar pull limpio. Solo entonces reconsiderar el cierre de RELEASE-02 y la etiqueta oficial.

## Propuesta de publicación futura, no ejecutada

Registro recomendado para evaluar: GHCR junto al repositorio. Nombres propuestos: `ghcr.io/juanfe28/aeroguard-backend`, `aeroguard-frontend`, `aeroguard-ai-service`, `aeroguard-simulator`. No se comprobó disponibilidad de nombres ni permisos de paquetes. No se creó PAT ni se solicitó un secreto en el chat.

El manifiesto deberá registrar versión, commit, fecha UTC, plataforma, digest por imagen, hash de SBOM y resultado de pruebas. No usar `latest` como único identificador de entrega. No automatizar despliegue ni publicación oficial al hacer push de código mientras falte el acuerdo de aprobación.
