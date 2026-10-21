# AeroGuard — Auditoría y preparación de Release

Fecha de corte: **21 de octubre de 2026, America/Bogota**. Repositorio inspeccionado: `D:\aeroguard`, rama `main`, base `28c955f3c283133ac755e1a6470aece5842bbbea`. Los cambios de esta auditoría están en el árbol de trabajo y no constituyen una publicación.

**Decisión:** prototipo académico demostrable; preparación de Release en curso. No está validado para venderse como detector autónomo de drones ni para operar como control de seguridad crítico.

## Informes, en el orden solicitado

1. [Estado actual y diagnóstico técnico](01_ESTADO_ACTUAL.md).
2. [Diagnóstico y matriz de RELEASE](02_RELEASE.md).
3. [Investigación comercial y competidores](03_INVESTIGACION_COMERCIAL.md).
4. [Documentación y pertinencia normativa](04_DOCUMENTACION_Y_NORMATIVA.md).
5. [Plan maestro académico y comercial](05_PLAN_MAESTRO.md).

Complementos: [fuentes externas](06_FUENTES.md), [guía de operación y verificación académica](07_GUIA_RELEASE.md), [notas de candidata](08_NOTAS_CANDIDATA.md) y [CHANGELOG](../../CHANGELOG.md).

## Evidencias principales

| Evidencia | Ubicación | Alcance |
|---|---|---|
| Estado de Git antes de modificar | [estado-inicial.txt](evidencias/estado-inicial.txt) | Incluye dos eliminaciones locales previas, conservadas |
| Planificación real de Release | [trello-alcance.json](evidencias/trello-alcance.json) | Extracto mínimo del JSON aportado, con SHA-256 del original; sin miembros ni correos |
| Reproducción del código base | [baseline/pytest.txt](evidencias/baseline/pytest.txt) | 64 aprobadas; cobertura 70,26 % en este entorno |
| Defectos reproducidos antes de corregir | [baseline/regresiones.txt](evidencias/baseline/regresiones.txt) | 12 fallos y 1 control positivo |
| Pruebas después de las correcciones | [cierre/summary.json](evidencias/cierre/summary.json) | 79 funcionales y 3 de carga; revisar límites del informe 1 |
| Cobertura actual | [cierre/coverage.json](evidencias/cierre/coverage.json) | 72,28 % de líneas de `backend/app`; no precisión de IA |
| Dependencias | [baseline/dependencias.json](evidencias/baseline/dependencias.json) | 65 avisos en 11 paquetes del entorno, sin evaluación de explotabilidad |
| Triaje inicial | [triaje-dependencias.csv](evidencias/triaje-dependencias.csv) | Runtime separado de herramientas; ningún aviso se acepta automáticamente |
| Trazabilidad del código | [referencias-codigo.json](evidencias/referencias-codigo.json) y [manifiesto-fuentes.json](evidencias/manifiesto-fuentes.json) | Rutas/líneas y SHA-256 de fuentes; sin crear un commit |
| Demo en navegador | [selenium-cierre.txt](evidencias/selenium-cierre.txt) y [captura](evidencias/selenium-cierre/evidencia_selenium_mapa.png) | Edge sin ventanas, perfil temporal, modo demo |
| Contrato API del código actual | [openapi-actual.json](evidencias/openapi-actual.json) | Exportación de la aplicación; no reemplaza los documentos históricos |

`evidencias/final/` conserva un intento intermedio fallido y `evidencias/verificado/` una ejecución aprobada previa a los dos casos adicionales de límite/formato. La ejecución definitiva es `evidencias/cierre/`. Los documentos antiguos y ZIP de TEST se mantienen como evidencia histórica; sus resultados no se han sustituido por los nuevos.

## Pendientes que impiden cerrar Release

- Revisar y resolver, o aceptar explícitamente con justificación académica, los avisos de dependencias. No equivalen a 65 ataques demostrados.
- Construir y ejecutar las imágenes con Docker y probar PostgreSQL; motor Docker no disponible durante esta auditoría.
- Validar los criterios con la rúbrica docente, que no está incluida en Trello.
- Autorizar y realizar la publicación de imágenes de RELEASE-02. No se publicó ningún artefacto, versión ni servicio público.

La investigación comercial es preliminar y documental. No se realizaron entrevistas, ventas, contactos a terceros ni pruebas de campo.
