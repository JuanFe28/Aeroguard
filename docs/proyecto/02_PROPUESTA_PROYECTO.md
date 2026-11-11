# AeroGuard — Propuesta del proyecto

Versión: 10-11-2026. Documento base para formularios de convocatorias de ciencia, tecnología e innovación, fondos de emprendimiento y becas. Cada sección corresponde a un campo habitual de esos formularios y puede copiarse y ajustarse a la extensión que pida cada entidad.

Los textos entre corchetes `[por completar]` requieren datos que solo el equipo puede aportar.

## 1. Identificación

| Campo | Contenido |
|---|---|
| Título | AeroGuard: plataforma de gestión e integración de eventos de aeronaves no tripuladas para la protección de zonas restringidas |
| Área temática | Seguridad y defensa · Tecnologías de la información · Inteligencia artificial · Industria 4.0 |
| Tipo de proyecto | Desarrollo tecnológico e innovación (paso de prototipo de laboratorio a piloto) |
| Institución | Unidades Tecnológicas de Santander (UTS) `[confirmar grupo de investigación y código]` |
| Lugar de ejecución | Bucaramanga, Santander, Colombia |
| Duración propuesta | 12 meses |
| Madurez inicial y final | TRL 4 → TRL 6 ([sustento](03_MADUREZ_TECNOLOGICA_TRL.md)) |
| Responsable | `[nombre, cargo, correo institucional]` |

## 2. Planteamiento del problema

Las aeronaves no tripuladas son cada vez más accesibles. Eso multiplica los sobrevuelos no autorizados sobre aeropuertos, infraestructura crítica, instalaciones industriales, eventos masivos y campus, con riesgos para la seguridad operacional, la privacidad y la seguridad física.

Quien debe proteger un sitio enfrenta tres dificultades:

1. **Información dispersa.** Radares, cámaras y analizadores de radiofrecuencia entregan datos en formatos y consolas distintas. El operador debe correlacionarlos a mano.
2. **Falsas alarmas y omisiones.** Aves u otros objetos disparan avisos; revisar cada uno satura al operador, y un aviso real puede perderse entre el ruido.
3. **Soluciones fuera de alcance.** Las plataformas comerciales son extranjeras, integran hardware propietario y se venden por proyecto. No se encontró soporte local verificado en Colombia ni precios públicos ([estudio comercial](../auditoria-2026-10-21/03_INVESTIGACION_COMERCIAL.md)).

En Colombia hay una señal concreta de necesidad: CODALTEC publicó en 2026 requerimientos de integración C-UAS y de prueba de concepto de radar para aeronaves no tripuladas, y la Aeronáutica Civil publica restricciones y zonas para UAS. No existe, hasta donde se pudo verificar, una plataforma nacional abierta que permita a universidades, integradores y operadores pequeños entrenar, integrar sensores y gestionar estos eventos.

**Pregunta que orienta el proyecto:** ¿puede una plataforma de software desarrollada localmente integrar fuentes reales de detección y apoyar de forma medible la decisión de un operador humano ante la presencia de drones en una zona restringida?

## 3. Justificación

- **Pertinencia.** El problema está reconocido por autoridades y entidades colombianas, y la respuesta actual depende de tecnología importada.
- **Capacidad nacional.** Un desarrollo propio forma talento en inteligencia artificial, sistemas geoespaciales y ciberseguridad, y deja el conocimiento en la región.
- **Viabilidad.** Ya existe un prototipo funcional, probado y desplegado en un servidor, con evidencias públicas. La inversión se dirige a validarlo en condiciones reales, no a empezar de cero.
- **Responsabilidad.** El proyecto limita su alcance a la detección, la gestión y la decisión humana. Excluye expresamente la neutralización y la interferencia, que requieren autorizaciones que el equipo no tiene.

## 4. Objetivos

### Objetivo general

Validar en un entorno real y supervisado una plataforma de software que integre fuentes de detección de aeronaves no tripuladas y apoye la gestión de alertas, la respuesta del operador y la trazabilidad de incidentes en zonas restringidas.

### Objetivos específicos

1. **Integrar** al menos una fuente de datos real y autorizada (cámara o sensor) con identidad, unidades y origen verificables.
2. **Construir y evaluar** un modelo de detección visual de drones con un conjunto de datos propio y una prueba ciega, reportando precisión, omisiones, falsas alarmas por hora y latencia.
3. **Endurecer** la plataforma para operación continua: seguridad, monitoreo en el servidor, respaldo automático y notificaciones externas.
4. **Validar la necesidad** con usuarios potenciales mediante entrevistas y definir el alcance de un producto mínimo viable.
5. **Ejecutar un piloto supervisado** con un aliado y medir su utilidad con indicadores acordados previamente.
6. **Formalizar** la titularidad, la licencia y el modelo de sostenibilidad del proyecto.

## 5. Estado del arte y antecedentes

**Soluciones comerciales.** DedroneTracker.AI (Axon, EE. UU.), DroneSentry-C2 (DroneShield, Australia), SkyDome (Fortem, EE. UU.) y AARTOS (Aaronia, Alemania) ofrecen fusión de radar, radiofrecuencia, video y acústica con consolas de mando. Todas dependen de hardware especializado. La comparación detallada, con fuentes, está en la [investigación comercial](../auditoria-2026-10-21/03_INVESTIGACION_COMERCIAL.md).

**Antecedentes propios.** AeroGuard nació como proyecto académico en las UTS y recorrió un ciclo DevOps completo:

| Fecha | Hito | Evidencia |
|---|---|---|
| 15-10-2026 | Fases Plan, Code y Build de la versión 1.1.0 | [Planificación](../PLANIFICACION_V1.1.md) |
| 21-10-2026 | Auditoría técnica, comercial y normativa; correcciones de seguridad | [Auditoría](../auditoria-2026-10-21/README.md) |
| 26-10-2026 | Publicación de la candidata `1.2.0-rc.1` y cuatro imágenes de contenedor | [Changelog](../../CHANGELOG.md) |
| 28-10-2026 | Instalación verificada en servidor privado con respaldo y restauración | [Resultado](../../deploy/RESULTADO_2026_10_28.md) |
| 29-10-2026 | Aceptación de interfaz con 51 casos de navegador | [QA](../qa-2026-10-29/README.md) |
| 01-11-2026 | Módulo académico de minería de datos (CRISP-DM, datos sintéticos) | [Informe](../MINERIA_DATOS_CRISP_DM.md) |
| 10-11-2026 | Integración en la rama principal y preparación de `1.2.0-rc.2` | [README](../../README.md) |

## 6. Metodología

El proyecto se ejecuta en cinco fases. Cada una termina con una decisión documentada de continuar, ajustar o detener.

| Fase | Meses | Actividades principales | Entregable |
|---|---|---|---|
| 1. Validación del problema | 1–2 | 8 a 12 entrevistas con operadores, integradores y responsables de compra; selección de un segmento y un aliado | Informe de entrevistas anonimizado y definición del producto mínimo viable |
| 2. Integración de fuente real | 2–5 | Adaptador para una cámara o sensor autorizado; autenticación del sensor; registro de unidades y referencia de altitud | Fuente real integrada y probada; contrato de datos |
| 3. Detección validada | 3–8 | Captura y anotación de imágenes con permisos; entrenamiento; evaluación ciega separada por sitio y fecha | Conjunto de datos documentado, modelo e informe de ensayo |
| 4. Preparación operativa | 6–9 | Monitoreo en el servidor, respaldo periódico, notificaciones, pruebas de carga, revisión de seguridad y de datos personales | Versión estable `1.2.0` y manual de operación actualizado |
| 5. Piloto supervisado | 9–12 | Operación con el aliado, doble verificación humana, medición de indicadores y soporte | Acta del piloto, informe de resultados y plan de sostenibilidad |

**Método de desarrollo.** Iteraciones cortas con integración continua en GitHub Actions, pruebas automatizadas como puerta de calidad, versiones semánticas y evidencias guardadas en el repositorio. El protocolo de validación de la detección está descrito en el [plan maestro](../auditoria-2026-10-21/05_PLAN_MAESTRO.md).

**Principio ético.** Revisión humana obligatoria. El sistema no ejecuta acciones automáticas sobre terceros.

## 7. Resultados esperados e indicadores

| Objetivo | Resultado | Indicador verificable | Meta |
|---|---|---|---|
| 1 | Fuente real integrada | Sensores o cámaras reales enviando datos a la plataforma | ≥ 1 |
| 2 | Modelo evaluado | Informe de ensayo ciego con precisión, omisiones, falsas alarmas por hora y latencia P95 | 1 informe; umbrales acordados con el usuario antes del ensayo |
| 3 | Plataforma estable | Versión `1.2.0` publicada; disponibilidad medida durante el piloto | `[meta por acordar con el aliado]` |
| 4 | Necesidad validada | Entrevistas realizadas y documentadas | 8 a 12 |
| 5 | Piloto ejecutado | Acta firmada por el aliado; incidentes gestionados; tiempo de respuesta medido | 1 piloto de `[n]` semanas |
| 6 | Proyecto formalizado | Acuerdo de titularidad, licencia definida y registro de software ante la DNDA | 3 documentos |
| Transversal | Formación | Estudiantes vinculados; trabajos de grado; ponencia o artículo | `[por completar]` |

No se fijan aquí porcentajes de precisión: se acordarán con el usuario según las consecuencias de cada tipo de error, antes de medir.

## 8. Cronograma

| Actividad | M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Entrevistas y definición del MVP | ■ | ■ | | | | | | | | | | |
| Integración de fuente real | | ■ | ■ | ■ | ■ | | | | | | | |
| Datos, entrenamiento y evaluación | | | ■ | ■ | ■ | ■ | ■ | ■ | | | | |
| Preparación operativa | | | | | | ■ | ■ | ■ | ■ | | | |
| Piloto supervisado | | | | | | | | | ■ | ■ | ■ | ■ |
| Formalización jurídica | ■ | ■ | ■ | | | | | | | | | |
| Divulgación e informe final | | | | | | | | | | | ■ | ■ |

## 9. Riesgos y mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| No conseguir acceso a un sensor o a un sitio de pruebas | Media | Alto | Iniciar con una cámara óptica propia en el campus; buscar aliado integrador desde el mes 1 |
| Datos insuficientes para entrenar el modelo | Media | Alto | Combinar conjuntos públicos con captura propia; reportar resultados por escenario sin extrapolar |
| Falsas alarmas que restan utilidad | Alta | Medio | Doble verificación humana; ajustar umbrales con el usuario; medir falsas alarmas por hora |
| Restricciones para volar drones de prueba | Media | Medio | Coordinar con un operador autorizado y cumplir el RAC vigente de la Aeronáutica Civil |
| Tratamiento de datos personales en video | Media | Alto | Evaluación previa según la Ley 1581 de 2012; minimización, avisos y retención limitada |
| Titularidad del software sin definir | Alta | Alto | Acuerdo entre autores e institución en los tres primeros meses |
| Rotación del equipo estudiantil | Alta | Medio | Documentación ordenada, pruebas automatizadas y traspasos registrados |
| Uso del sistema fuera de su alcance | Baja | Alto | Límites declarados en contrato y en la interfaz; sin funciones de neutralización |

## 10. Impacto esperado

- **Tecnológico:** plataforma nacional validada en entorno real y un conjunto de datos local documentado.
- **Académico:** formación de estudiantes en IA, sistemas geoespaciales, DevOps y ciberseguridad; trabajos de grado y publicaciones.
- **Económico:** base para un emprendimiento de base tecnológica o una transferencia a un integrador.
- **Social e institucional:** mejor capacidad de respuesta de quienes protegen sitios sensibles, con evidencia auditable.

## 11. Sostenibilidad

Al terminar, el proyecto debe poder continuar por una de estas vías, que se evaluarán con los resultados del piloto: licencia académica para formación, implementación local con mantenimiento para un integrador, o transferencia a una entidad aliada. Las hipótesis están en el [modelo de negocio](05_MODELO_DE_NEGOCIO.md).

## 12. Consideraciones éticas, legales y ambientales

- Sin neutralización, interferencia ni identificación de personas.
- Cumplimiento condicionado de datos personales, operación de aeronaves y uso del espectro, según la [matriz normativa](../auditoria-2026-10-21/04_DOCUMENTACION_Y_NORMATIVA.md).
- Impacto ambiental bajo: proyecto de software con equipos de cómputo y sensores de baja potencia.

## 13. Presupuesto y equipo

Ver [Presupuesto y equipo](04_PRESUPUESTO_Y_EQUIPO.md).
