# Estado para actualizar Trello — 29 de octubre de 2026

Tablero identificado: [Aeroguard 🚀](https://trello.com/b/0LrfUef0/aeroguard-%F0%9F%9A%80).

Se contrastó la exportación guardada del 21 de octubre con evidencias posteriores del repositorio y una consulta actual de GitHub. **No se consultó ni modificó el tablero vivo**. Los títulos provienen de `docs/auditoria-2026-10-21/evidencias/trello-alcance.json`; salvo Release, la exportación no conserva enlaces individuales ni criterios detallados. Confirmar cualquier checklist adicional del tablero antes del cierre definitivo.

## Qué marcar

| Tarjeta | Evidencia disponible | Cierre propuesto |
|---|---|---|
| RELEASE-01 — SemVer y CHANGELOG | Política, changelog y candidata identificada | Terminada para v1.2.0-rc.1. No equivale a versión estable aceptada. |
| RELEASE-02 — Publicar imágenes | Release publicada y cuatro imágenes fijadas por digest en `deploy/release.json` | Terminada para la candidata publicada. |
| DEPLOY-01 — Pipeline CI/CD con GitHub Actions | Checks y ensayo de despliegue aprobados en a884c39; workflow de publicación ejecutado para la candidata | Terminada para el pipeline de candidata y ensayo. La instalación del servidor fue un procedimiento autorizado separado; no hay evidencia de despliegue automático al servidor en cada push. |
| DEPLOY-02 — Variables y despliegue en servidor/VM | Evidencia del 28/10: servidor privado, cuatro servicios saludables, aislamiento, login, persistencia tras reiniciar el stack y restauración | Terminada para el stack básico de la candidata en instalación privada. No cerrar como actualización de las correcciones del 29/10 ni como despliegue público con dominio/TLS. |
| OPERATE-01 — Procedimiento de respaldo/restauración PostgreSQL | Manual y restauración ensayada en base nueva; verificación adicional en servidor el 28/10, con archivos de reportes | Terminada para procedimiento y ensayo documentados. No acredita respaldo automático periódico ni simulacro de desastre completo. |
| OPERATE-02 — Manual de operaciones | `docs/correcciones-2026-10-21/OPERACION.md` para operador/analista | Terminada como entrega documental de la candidata. Actualizar el manual al preparar la siguiente versión y registrar aceptación si la rúbrica la exige. |
| MONITOR-01 — Prometheus y métricas FastAPI | Implementación y target local `up` documentados | Implementada y verificada localmente. Mantener parcial si se exige funcionamiento en el servidor desplegado: falta evidencia de esa instalación. |
| MONITOR-02 — Dashboard Grafana | Dashboard provisionado y cuatro paneles comprobados localmente | Implementada y verificada localmente. Mantener parcial para servidor por el mismo motivo. |
| MONITOR-03 — Healthcheck y alertas de sensores | Healthcheck, reglas y alerta `sensor_stale` en estado `firing` en prueba local | Implementada y verificada localmente. Falta prueba en servidor y receptor externo si la aceptación incluye entrega de notificaciones. |

MONITOR puede cerrarse con una anotación de «validación local» si ese es el criterio académico de las tarjetas. **No marcar las tres como monitoreo operativo del servidor** con la evidencia actual. Tampoco introducir dominio público/TLS, respaldo automático o un receptor externo como requisitos retroactivos de una tarjeta cuyo checklist no los exige: son alcances separados que deben quedar explícitos.

## Evidencias para adjuntar o citar

- [Release publicada, candidata v1.2.0-rc.1](https://github.com/JuanFe28/Aeroguard/releases/tag/v1.2.0-rc.1), confirmada como prerelease, no borrador.
- [Publicación de microservicios](https://github.com/JuanFe28/Aeroguard/actions/runs/40342511908); digests y commit de imágenes en `deploy/release.json`.
- [Verificación académica del HEAD a884c39](https://github.com/JuanFe28/Aeroguard/actions/runs/40706149061): checks aprobados, construcción manual de contenedores omitida en esa ejecución.
- [Ensayo de Deploy del HEAD a884c39](https://github.com/JuanFe28/Aeroguard/actions/runs/40706149053): aprobado.
- Instalación y restauración del servidor: [resultado](../../deploy/RESULTADO_2026_10_28.md) y [evidencia saneada](../../deploy/evidence/2026-10-28-server.json). Describen el 28/10, no una comprobación en vivo del 29/10.
- Operación: [manual](../correcciones-2026-10-21/OPERACION.md).
- Monitoreo local: [evidencia](../correcciones-2026-10-21/evidencias/monitoring.json).

## Lo que falta después del despliegue básico

Preparación adicional: 51 casos de navegador ensayados localmente, con contraste/accesibilidad y capturas de once pantallas en tres tamaños. El paso 5 del TXT lanza esa misma batería sobre QA del destino. Adjuntar el resultado del servidor y la aceptación visual por pantalla a TEST/Deploy; no cerrar aceptación del servidor solo por este ensayo SQLite. [Matriz de cobertura](PRUEBA_COMPLETA_APP.md).

1. **Cerrar la revisión del código:** el [PR #1](https://github.com/JuanFe28/Aeroguard/pull/1) sigue abierto y en borrador, sin fusionar. Las correcciones están publicadas en `codex/qa-continuation`, [PR #2](https://github.com/JuanFe28/Aeroguard/pull/2). Los checks del checkpoint `9453997` aprobaron; verificar los del HEAD final antes de ejecutar.
2. **Terminar QA del destino:** permisos por rol, estados de usuarios y recorrido detecciones/alertas/reportes/auditoría ya tienen pruebas automatizadas locales con usuarios persistidos y login real. Resultado acumulado: 175 aprobadas, 7 omitidas por falta de Compose, 7 subpruebas aprobadas y 10 frontend aprobadas. Falta PostgreSQL y aceptación visual del destino; usar [ACEPTACION_SERVIDOR.md](ACEPTACION_SERVIDOR.md).
3. **Preparar la siguiente candidata:** verificar Docker/Linux y PostgreSQL, publicar imágenes nuevas con otra etiqueta y actualizar el servidor desde un equipo con identidad SSH autorizada. El servidor documentado conserva imágenes de `33f1cfd`, no los arreglos nuevos de configuración, SOAR, usuarios, mapas, trayectorias y scheduler.
4. **Instalar y verificar monitoreo en el destino privado:** recolección Prometheus, paneles Grafana y fallos controlados de backend/sensor. Acordar y comprobar el receptor externo si se requiere notificación.
5. **Completar operación según aceptación:** SMTP y recuperación de contraseña con entrega real; n8n externo si forma parte del alcance. Sensores físicos, precisión de visión, referencia de altitud y rendimiento del destino requieren validaciones propias.

El anclaje externo de auditoría, respaldo periódico, ensayo de reinicio del anfitrión y recuperación ante caída real son pendientes operativos adicionales, no pruebas ya realizadas. Los reportes programados tienen ocho pruebas nuevas de recuperación local, pero ese arreglo todavía no está en las imágenes del servidor.

## Texto breve para la tarjeta de Deploy

> Candidata v1.2.0-rc.1 instalada y verificada en servidor privado el 28/10/2026: PostgreSQL/PostGIS, RabbitMQ, backend y frontend saludables; acceso mediante túnel SSH, persistencia y restauración ensayadas. El cierre corresponde al stack básico de esa candidata. Las correcciones del 29/10 están publicadas en el PR #2 y requieren nueva candidata, validación y actualización del destino. Monitoreo del servidor y QA del destino se registran como pendientes separados.

## Texto breve para las tarjetas de Monitor

> Implementación y prueba local documentadas: métricas protegidas, target Prometheus activo, dashboard Grafana de cuatro paneles y alerta de sensor vencido comprobada. Pendiente instalar/verificar en el servidor privado; la prueba local no acredita notificaciones entregadas a un receptor externo.
