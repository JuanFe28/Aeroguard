# Mapa de la documentación de AeroGuard

Actualizado: 10-11-2026. Este índice ordena toda la documentación del repositorio por propósito. Empieza aquí.

**AeroGuard en una frase:** plataforma de software, desarrollada en las Unidades Tecnológicas de Santander (UTS), para recibir observaciones de objetos aéreos, vigilar zonas restringidas, generar alertas y dejar trazabilidad de las decisiones de un operador humano. Es un prototipo académico validado en laboratorio; todavía no detecta drones con sensores reales.

## Cómo leer este mapa

| Estado | Significado |
|---|---|
| **Vigente** | Describe el proyecto como está hoy. Úsalo como referencia. |
| **Histórico** | Registro fechado de una sesión de trabajo. Se conserva como evidencia y no se actualiza. Puede contener pendientes ya resueltos. |
| **Plantilla** | Estructura lista que el equipo debe completar con datos propios (cifras, nombres, firmas). |

## 1. Para entender el proyecto (empieza aquí)

| Documento | Para qué sirve | Estado |
|---|---|---|
| [Resumen ejecutivo](proyecto/01_RESUMEN_EJECUTIVO.md) | Qué es, qué problema atiende, qué está hecho y qué falta, en dos páginas | Vigente |
| [README del repositorio](../README.md) | Estado comprobado, instalación local y con Docker | Vigente |
| [Arquitectura técnica](tecnica/ARQUITECTURA.md) | Componentes, flujo de datos, modelo de datos y seguridad | Vigente |
| [Manual de usuario](tecnica/MANUAL_DE_USUARIO.md) | Roles, módulos de la interfaz y tareas habituales | Vigente |

## 2. Para postular a convocatorias, fondos y becas

| Documento | Para qué sirve | Estado |
|---|---|---|
| [Guía de postulación](proyecto/06_GUIA_DE_POSTULACION.md) | Qué pide normalmente una convocatoria, dónde está cada respuesta y qué falta conseguir | Vigente |
| [Propuesta del proyecto](proyecto/02_PROPUESTA_PROYECTO.md) | Problema, justificación, objetivos, metodología, resultados, cronograma, riesgos e impacto | Vigente |
| [Madurez tecnológica (TRL)](proyecto/03_MADUREZ_TECNOLOGICA_TRL.md) | Nivel de madurez sustentado con evidencias y ruta al siguiente nivel | Vigente |
| [Presupuesto y equipo](proyecto/04_PRESUPUESTO_Y_EQUIPO.md) | Rubros, equipo y contrapartida | Plantilla |
| [Modelo de negocio](proyecto/05_MODELO_DE_NEGOCIO.md) | Lean Canvas con hipótesis por validar | Vigente (hipótesis) |
| [Investigación comercial](auditoria-2026-10-21/03_INVESTIGACION_COMERCIAL.md) | Segmentos, competidores, FODA y límites del estudio | Vigente |
| [Documentación y normativa en Colombia](auditoria-2026-10-21/04_DOCUMENTACION_Y_NORMATIVA.md) | Matriz de normas aplicables y documentos empresariales pendientes | Vigente |
| [Plan maestro de evolución](auditoria-2026-10-21/05_PLAN_MAESTRO.md) | Camino académico y comercial, backlog priorizado | Vigente |
| [Trayectorias y autoridades](qa-2026-10-29/TRAYECTORIAS_Y_AUTORIDADES.md) | Entidades reguladoras colombianas relacionadas | Vigente |
| [Fuentes externas](auditoria-2026-10-21/06_FUENTES.md) | Fuentes consultadas y límites de la investigación | Vigente |

## 3. Para instalar, operar y publicar

| Documento | Para qué sirve | Estado |
|---|---|---|
| [Manual de operación y recuperación](correcciones-2026-10-21/OPERACION.md) | Arranque, monitoreo, respaldo y restauración | Vigente |
| [Despliegue privado](../deploy/README.md) | Instalación en servidor Linux con imágenes fijadas por digest | Vigente (candidata rc.1) |
| [Ubuntu con Docker rootless](../deploy/ubuntu-rootless.md) | Preparación del servidor | Vigente |
| [Política de versionado](../VERSIONING.md) | SemVer, candidatas y pasos de Release | Vigente |
| [Changelog](../CHANGELOG.md) | Cambios por versión | Vigente |
| [Siguiente candidata](qa-2026-10-29/SIGUIENTE_CANDIDATA.md) | Puertas pendientes antes de publicar rc.2 | Vigente |
| [Comandos del servidor](../COMANDOS_SERVIDOR_CASA.txt) | Pasos para retomar desde el portátil autorizado | Vigente |
| [Aceptación del servidor](qa-2026-10-29/ACEPTACION_SERVIDOR.md) | Lista de aceptación pendiente en el destino | Vigente |

## 4. Diseño, requisitos y referencia técnica

| Documento | Para qué sirve | Estado |
|---|---|---|
| [Planificación e ingeniería de requisitos v1.1](PLANIFICACION_V1.1.md) | Historias de usuario, criterios Gherkin, contratos de API y diseño | Histórico (diseño de v1.1.0) |
| [Especificación OpenAPI](AeroGuard_OpenAPI.json) | Contrato de la API | Vigente |
| [Colección Postman](AeroGuard_Postman_Collection.json) y carpeta `postman/` | Peticiones de ejemplo | Vigente |
| [Minería de datos CRISP-DM](MINERIA_DATOS_CRISP_DM.md) | Ejercicio académico con **datos sintéticos**; no mide detección real | Vigente (académico) |
| [Estructura del repositorio](../Estructura.txt) | Árbol de carpetas comentado | Histórico |

## 5. Calidad, pruebas y evidencias

| Documento | Para qué sirve | Estado |
|---|---|---|
| [QA del 29-10-2026](qa-2026-10-29/README.md) | Último estado de pruebas y correcciones | Vigente |
| [Batería completa de la aplicación](qa-2026-10-29/PRUEBA_COMPLETA_APP.md) | Matriz de 51 casos de navegador y límites de cobertura | Vigente |
| [Recuperación del scheduler](qa-2026-10-29/SCHEDULER_RECUPERACION.md) | Diseño y pruebas de reportes programados | Vigente |
| [Estado para Trello](qa-2026-10-29/ESTADO_TRELLO.md) | Qué tarjetas pueden cerrarse y con qué evidencia | Vigente |
| [Correcciones del 21-10-2026](correcciones-2026-10-21/README.md) | Correcciones verificadas y evidencias | Histórico |
| [Auditoría del 21-10-2026](auditoria-2026-10-21/README.md) | Informes 1 a 8 de la auditoría inicial | Histórico (informes 3, 4 y 5 siguen vigentes) |
| [QA del 28-10-2026](qa-2026-10-28/README.md) | Revisión parcial de interfaz interrumpida | Histórico |
| [Resultado del despliegue del 28-10-2026](../deploy/RESULTADO_2026_10_28.md) | Evidencia de la instalación en servidor privado | Histórico |
| `TRELLO_TEST_01/02/03.md`, `RESULTADOS_TEST_TRELLO.md`, `*.zip` | Evidencias de la fase TEST | Histórico |
| [Guía de exposición](GUIA_EXPOSICION_LUNES.md) | Guion de la exposición de la fase TEST | Histórico (cifras desactualizadas) |

## 6. Notas internas de continuidad

`promt de continuacion.txt`, `LEEME_PUBLICAR_CASA.txt` y `qa-2026-10-29/ENTREGA_CASA.md` son notas de traspaso entre sesiones de trabajo. Son históricas y no describen el producto.

## Reglas para mantener el orden

1. Un documento nuevo va en `docs/proyecto/` (propósito, postulación, negocio) o en `docs/tecnica/` (cómo funciona y cómo se usa). Los registros de una sesión van en una carpeta fechada `docs/<tema>-AAAA-MM-DD/`.
2. Los documentos históricos no se reescriben. Si algo cambió, se corrige el documento vigente y se anota en el changelog.
3. Toda afirmación sobre el producto distingue lo **comprobado** (con evidencia en el repositorio), lo **simulado** y lo **pendiente**. No se publican cifras de precisión, mercado o costos que no tengan fuente.
4. Cada documento nuevo se agrega a este mapa.
