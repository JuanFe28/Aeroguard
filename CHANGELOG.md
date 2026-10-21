# Changelog

Este registro describe el código y la preparación local. No prueba que haya versiones publicadas. La política SemVer propuesta está en `docs/auditoria-2026-10-21/02_RELEASE.md`.

## [Unreleased]

### Corregido

- Se exigen autenticación y permisos en telemetría y dictámenes operativos.
- La verificación de auditoría utiliza el mismo génesis que la escritura.
- Se rechazan imágenes corruptas y cargas superiores a 10 MiB; se limitan dimensiones.
- Visión identifica el motor utilizado y declara que no está validado; YOLO solo acepta clases explícitas de dron.
- La telemetría sin análisis de imagen no atribuye resultados de IA ni confianza constante.
- Demo y reportes indican datos sintéticos; las reglas locales no recomiendan interferencia ni atribuyen intención hostil.
- APP_VERSION predeterminado se alinea con la identificación interna existente 1.1.0.
- Empaquetado del backend preparado con requisitos de test/detector, un worker y ruta persistente de reportes coherente. Construcción Docker pendiente de verificar.

### Añadido

- Quince casos nuevos de regresión y validación de entradas; verificador de Release con evidencias por ejecución.
- CI y construcción manual de imágenes sin publicación; todavía no ejecutados en GitHub.
- Auditoría, matriz de Release, investigación comercial con fuentes, inventario documental, roadmap, guía y notas de candidata.
- Opciones de Selenium sin ventana y carpeta de evidencias configurable.

### Pendiente

- Triaje de vulnerabilidades de dependencias, build/smoke con Docker, PostgreSQL, restauración, aceptación académica y publicación autorizada de imágenes.
- Validación real de detección y cierre de brechas de integración/operación antes de piloto o comercialización.

## [1.1.0 — identificación interna, sin tag publicado]

- `076b0b6` — 15-10-2026: base registrada de planificación, implementación y empaquetado. Las afirmaciones históricas de IA/PostGIS deben contrastarse con la auditoría.
- `28c955f` — 19-10-2026: demo local, ampliación de pruebas de API y correcciones de seguridad. Evidencia histórica: 64 pruebas funcionales y 3 de carga, cobertura 70,21 % y Bandit 0 medios/altos con 17 bajos.

No se identificaron etiquetas remotas en la consulta del 21-10-2026. Las notas de una candidata futura deberán referenciar el commit y los digests realmente aprobados.
