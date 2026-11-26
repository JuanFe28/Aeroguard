# AeroGuard · Tablero y fichas de trabajo

El equipo ya realizó una prueba simulada por cuestiones de costo. El trabajo actual es documentar esa prueba, revisar sus resultados y preparar los recursos para la prueba de campo. La validación en campo es un hito obligatorio del proyecto y su fecha queda por confirmar. Los umbrales se acuerdan antes de ejecutar cada tarea. [Ficha del proyecto](https://www.ciaiuts.com/app/proyectos/aeroguard) · [Tablero del CIAI Hub](https://www.ciaiuts.com/app/tableros/aeroguard)

## Cómo se organiza el trabajo

- **Hito (`H0`, `H1`…)**. Resultado mayor con una puerta de aprobación.
- **Tarea (`H0-01`, `H0-02`…)**. Unidad de trabajo con una ficha, una persona responsable y otra que revisa. Usa el mismo código en la ficha, en la tarjeta y en su evidencia.
- **Actividad**. Acción concreta dentro del método. Cada actividad se asigna a una persona. Las horas de las fichas estiman trabajo humano activo. Registra aparte las esperas, el tiempo de cómputo y el plazo calendario.

### Hitos y puertas de avance

| Hito | Cuándo se trabaja | Puerta de aprobación |
| --- | --- | --- |
| **H0 · Organizar la etapa actual y preparar recursos** | Ahora, en paralelo con H1 | El asesor revisa la entrega de la fase simulada. Quedan identificados responsables, revisores, versión de referencia y recursos de campo pendientes. |
| **H1 · Documentar y revisar la prueba simulada** | Ahora | Una segunda persona revisa el informe, verifica su evidencia y confirma que están documentadas las limitaciones de la simulación. |
| **H2 · Preparar y ejecutar la prueba de campo** | Preparación desde ahora. Ejecución cuando estén disponibles los recursos y se apruebe el protocolo. | El asesor revisa el protocolo aprobado antes de ejecutar, la evidencia y los resultados de campo. |
| **H3 · Entregar y sustentar el proyecto** | Después de H2 | El evaluador registra el estado de cada entregable y revisa el informe con resultados de simulación y de campo. |
| **H4 · Validar con usuarios y preparar la oferta** | Entrevistas desde ahora. Piloto y oferta después de campo. | Un usuario revisa el piloto y sus resultados. La institución revisa derechos, costos, alcance y soporte antes de que se decida ofrecer el producto. |

Un resultado por debajo de la meta puede aceptarse como hallazgo si el método se ejecutó conforme al protocolo y la evidencia permite revisarlo. Registra por separado la validez del ensayo, el cumplimiento de la meta y la aprobación del hito. Un ensayo sin evidencia suficiente requiere revisión o repetición. Para cada puerta guarda fecha, revisor, decisión y enlace a la evidencia.

## Tablero inicial

Empieza por **H1-01**, porque la prueba ya se hizo y su evidencia es el punto de partida. Trabaja **H0-02** en paralelo para identificar cómo financiar o conseguir prestados los recursos de campo. Mantén **H2-03** en **Pendiente** hasta contar con recursos, autorización y protocolo aprobado. El estado de cada ficha refleja el trabajo de esa tarjeta. Los roles se asignan a personas distintas al confirmarse el equipo.

| Tarjeta | Prioridad | Depende de |
| --- | --- | --- |
| **H0-01 · Acordar con el asesor la entrega de la fase simulada** | Ahora | — |
| **H0-02 · Preparar el presupuesto y los recursos para campo** | Ahora | — |
| **H0-03 · Identificar la versión de referencia** | Primera | — |
| **H0-04 · Definir el lugar de Ollama en la investigación** | Según aporte | — |
| **H1-01 · Documentar la prueba simulada realizada** | Primera | H0-03 para cerrar la ficha |
| **H1-02 · Revisar los resultados y límites de la simulación** | Ahora | H1-01 |
| **H1-03 · Verificar el flujo del prototipo en una versión común** | Ahora | H0-03 |
| **H1-04 · Actualizar el contrato de API y validar la telemetría** | Preparación | H0-03 |
| **H1-05 · Corregir y documentar la evaluación de minería** | Ahora | H1-02 |
| **H1-06 · Revisar el agente de apoyo y la automatización** | Preparación | H0-03 |
| **H1-07 · Cerrar los riesgos de operación que afectan al piloto** | Antes del piloto | H1-03, H1-04 |
| **H2-01 · Aprobar el protocolo de evaluación** | Preparación | H1-02 para cerrar el protocolo |
| **H2-02 · Evaluar el modelo en laboratorio e integrar el video** | Preparación | H2-01 y recursos disponibles |
| **H2-03 · Ejecutar y documentar la prueba de campo** | Hito obligatorio futuro | H2-02, recursos y autorización |
| **H3-01 · Preparar y sustentar la entrega** | Cierre del proyecto | H1-02 y H2-03 |
| **H4-01 · Validar el problema con usuarios y buscar un aliado** | Ahora | — |
| **H4-02 · Aclarar los derechos y las licencias con la universidad** | Preparación | — |
| **H4-03 · Validar el piloto con un usuario y medir el costo real** | Después de campo | H2-03, H1-07, H4-01 |
| **H4-04 · Definir qué se puede ofrecer y en qué condiciones** | Después del piloto | H4-02, H4-03 |

## Fichas de las tareas

### H0-01 · Acordar con el asesor la entrega de la fase simulada

- **Objetivo directo**. Acordar qué evidencia de la prueba simulada se presenta ahora, quién la revisa y cuándo.
- **Justificación**. El grupo necesita un entregable de esta etapa mientras prepara los recursos para el hito de campo.
- **Método**. 1. El líder reúne un resumen de la simulación y sus evidencias. 2. El líder revisa con el asesor el entregable, la fecha y los criterios. 3. El líder registra el acuerdo y las dependencias de campo.
- **KPI y umbral**. Un acta con entregable de la etapa, revisor, fecha de revisión, criterio de aceptación y registro de la prueba de campo pendiente.
- **Evidencia**. Acta de revisión de la fase simulada y confirmación del asesor.
- **Criterio de validez**. El asesor confirma el entregable de esta fase. El acta registra la validación de campo como parte del cierre del proyecto.
- **Responsable / revisor**. Líder del proyecto / asesor por confirmar.
- **Estimación**. 1–2 h de trabajo activo.

### H0-02 · Preparar el presupuesto y los recursos para campo

- **Objetivo directo**. Saber qué recursos requiere la prueba de campo, cuánto costarían y cómo conseguirlos.
- **Justificación**. El costo motivó la prueba simulada. Un presupuesto y opciones de acceso permiten planear la validación de campo.
- **Método**. 1. El líder lista equipos, cómputo, personal, espacio y permisos requeridos. 2. El equipo verifica qué puede aportar la universidad y registra alternativas de préstamo o financiación. 3. El líder asigna responsables y fechas de decisión.
- **KPI y umbral**. Una matriz en la que cada recurso indispensable tiene disponibilidad, costo estimado o por cotizar, opción de acceso y responsable.
- **Evidencia**. Matriz de recursos, presupuesto preliminar y registro de consultas o confirmaciones.
- **Criterio de validez**. Cada disponibilidad confirmada tiene una fuente y cada pendiente tiene fecha de revisión. El revisor comprueba qué dependencias faltan para programar el ensayo.
- **Responsable / revisor**. Líder del proyecto / asesor por confirmar.
- **Estimación**. 2–4 h de trabajo activo.

### H0-03 · Identificar la versión de referencia

- **Objetivo directo**. Elegir el commit y el entorno para las próximas verificaciones.
- **Justificación**. H0 necesita una base común porque las pruebas, las imágenes publicadas y el servidor pueden corresponder a versiones diferentes.
- **Método**. 1. Desarrollo compara `origin/main` con la candidata `1.2.0-rc.2`. 2. Desarrollo registra la versión histórica de la simulación si se puede recuperar y propone la versión para los nuevos ensayos. 3. El líder revisa la ficha.
- **KPI y umbral**. Una ficha con commit completo, versión, entorno, guía de arranque y estado de publicación e instalación.
- **Evidencia**. Ficha y enlace al commit y al manifiesto o registro disponible.
- **Criterio de validez**. El commit se puede identificar a partir del enlace. Los estados sin acceso o evidencia quedan marcados como pendientes de verificación.
- **Responsable / revisor**. Desarrollo / líder del proyecto. Si el líder asume desarrollo, se designa otra persona para revisar.
- **Estimación**. 2–4 h de trabajo activo.

### H1-01 · Documentar la prueba simulada realizada

- **Objetivo directo**. Recuperar y documentar lo que el equipo ya probó mediante simulación.
- **Justificación**. Los resultados existentes sirven como evidencia de la etapa inicial y orientan el diseño de la prueba de campo.
- **Método**. 1. QA reúne capturas, trazas e informes existentes. 2. QA reconstruye qué se probó, con qué versión, entorno y datos. 3. QA redacta el informe y registra los datos que no se pudieron recuperar.
- **KPI y umbral**. Un informe con escenario, versión, datos, procedimiento, resultados, evidencias y limitaciones. Los datos históricos faltantes se identifican con su efecto en la interpretación.
- **Evidencia**. Informe de simulación y enlaces a los archivos recuperados.
- **Criterio de validez**. Cada resultado usado para una conclusión tiene evidencia identificable. Se registra que el equipo eligió la simulación por costo y se indica cuáles resultados requieren validación en campo.
- **Responsable / revisor**. QA / responsable técnico distinto de la persona que ejecuta.
- **Estimación**. 3–6 h de trabajo activo.

### H1-02 · Revisar los resultados y límites de la simulación

- **Objetivo directo**. Confirmar qué conclusiones permite la simulación y qué preguntas quedan para campo.
- **Justificación**. El protocolo de campo debe partir de las brechas que dejó la prueba simulada.
- **Método**. 1. Investigación revisa cada conclusión frente a su evidencia. 2. Investigación identifica las preguntas que quedan abiertas. 3. El revisor valida el resumen. Si una conclusión indispensable carece de evidencia, se acuerda si se repite ese caso.
- **KPI y umbral**. Una revisión registrada y una lista de preguntas pendientes, cada una vinculada con la evidencia que se requiere obtener.
- **Evidencia**. Informe comentado, lista de preguntas de campo y registro de revisión.
- **Criterio de validez**. El revisor puede relacionar cada conclusión con el escenario simulado que la sustenta.
- **Responsable / revisor**. Responsable de investigación / asesor o integrante distinto de quien preparó el análisis.
- **Estimación**. 2–4 h de trabajo activo.

### H2-01 · Aprobar el protocolo de evaluación

- **Objetivo directo**. Acordar cómo se medirán el alcance, la detección, la proporción de alertas correctas y la latencia.
- **Justificación**. H2 necesita reglas de medición conocidas antes de observar los resultados.
- **Método**. 1. Investigación define qué cuenta como aparición, alerta correcta y aviso. 2. Investigación prepara un formato de registro. 3. El asesor revisa condiciones, metas y límites del ensayo autorizado.
- **KPI y umbral**. Cuatro indicadores con unidad, método, condiciones y umbral acordados por escrito. La ficha del Hub propone 100 m o más, detección de al menos 80 % de las apariciones, al menos 85 % de alertas correctas y aviso en menos de 3 s.
- **Evidencia**. Protocolo aprobado y formato de registro.
- **Criterio de validez**. La aprobación tiene fecha anterior al ensayo y define cómo tratar datos faltantes, repeticiones y condiciones que invalidarían una medición.
- **Responsable / revisor**. Responsable de investigación / asesor.
- **Estimación**. 4–8 h de trabajo activo.

### H2-02 · Evaluar el modelo en laboratorio e integrar el video

- **Objetivo directo**. Obtener una evaluación de laboratorio del modelo y comprobar que la fuente de video acordada alimenta el recorrido de prueba.
- **Justificación**. H2 necesita un ensayo de laboratorio y una revisión del flujo antes de dedicar recursos a campo.
- **Método**. 1. Investigación documenta origen, permisos y reparto de los datos. 2. Visión por computador selecciona, ajusta si hace falta y evalúa una versión del modelo. 3. Desarrollo integra el video acordado a un entorno aislado. 4. QA verifica el recorrido y registra incidencias.
- **KPI y umbral**. Una versión de modelo identificada, un inventario de datos, una evaluación de laboratorio y un ensayo documentado del flujo de video.
- **Evidencia**. Inventario de datos y permisos, versión evaluada y registro del ensayo.
- **Criterio de validez**. Se puede identificar la fuente y la versión. Los datos usados para evaluar se mantienen separados de los usados para ajustar el modelo.
- **Responsable / revisor**. Responsable técnico / QA distinto del responsable técnico.
- **Estimación**. 16–32 h de trabajo activo inicial. Ajustar el rango al confirmar datos y recursos. Registrar tiempo de cómputo por separado.

### H2-03 · Ejecutar y documentar la prueba de campo

- **Objetivo directo**. Obtener evidencia de campo sobre los indicadores acordados.
- **Justificación**. H2 requiere resultados obtenidos en las condiciones aceptadas por el grupo.
- **Método**. 1. Coordinación confirma condiciones y autorización. 2. El equipo de campo registra datos, incidencias y desviaciones. 3. Investigación calcula indicadores y entrega el informe para revisión.
- **KPI y umbral**. Una prueba de campo ejecutada con el protocolo aprobado y un informe con sus indicadores y resultados. Si un indicador obligatorio queda sin medición válida, el asesor registra si se repite o se enmienda el protocolo con su justificación. Las metas de desempeño son las aprobadas en H2-01.
- **Evidencia**. Registro del ensayo, resultados y documento de revisión.
- **Criterio de validez**. El asesor puede rastrear cada resultado hasta su evidencia y comprobar si se respetaron las condiciones acordadas. Una métrica faltante recibe una decisión explícita de repetición o limitación.
- **Responsable / revisor**. Coordinación de campo / asesor o integrante designado que no dirigió el ensayo.
- **Estimación**. 24–40 h de trabajo activo distribuidas.

### H3-01 · Preparar y sustentar la entrega

- **Objetivo directo**. Entregar el proyecto y dejar registrada la decisión del evaluador.
- **Justificación**. H3 reúne los resultados del proyecto y documenta lo que necesita continuidad.
- **Método**. 1. Documentación reúne fichas y evidencia. 2. El líder ensaya la sustentación con el equipo. 3. El evaluador revisa el paquete y registra su decisión.
- **KPI y umbral**. El 100 % de los entregables acordados en H0 tiene versión, enlace y decisión registrada.
- **Evidencia**. Informe, manuales, guía y guion de demostración, matriz de evidencias y acta de revisión.
- **Criterio de validez**. El acta identifica lo aceptado, lo que requiere corrección y lo que quedó fuera del alcance acordado. Los pendientes tienen responsable y fecha.
- **Responsable / revisor**. Líder de documentación / evaluador designado.
- **Estimación**. 12–16 h de trabajo activo distribuidas.

## Fichas añadidas después de revisar el repositorio

El [informe de revisión](08_REVISION_INTEGRAL_Y_RUTA_DE_VALIDACION.md) enlaza la evidencia de cada frente con estas tarjetas. Las tareas de descubrimiento comercial se pueden adelantar mientras se consiguen recursos. La aprobación del hito de mercado requiere resultados de campo y del piloto.

### H0-04 · Definir el lugar de Ollama en la investigación

- **Objetivo directo**. Determinar si la instrumentación de Ollama responde a una pregunta de AeroGuard.
- **Justificación**. El laboratorio local tiene objetivos y evidencias propios.
- **Método**. Inventariar artefactos, formular la pregunta y revisar con el asesor si existe una dependencia del producto.
- **KPI y umbral**. Una decisión escrita con pregunta, responsable y evidencia requerida cuando se decida integrar.
- **Evidencia**. Ficha de alcance y enlaces al laboratorio local.
- **Criterio de validez**. El acta identifica el experimento por su nombre y evita confundir sus resultados con visión o campo.
- **Responsable / revisor**. Líder de investigación / asesor distinto del autor.
- **Estimación**. 1–3 h de trabajo activo.

### H1-03 · Verificar el flujo del prototipo en una versión común

- **Objetivo directo**. Reproducir el recorrido de trabajo que se mostrará al grupo.
- **Justificación**. Una demostración reproducible vincula el código y las evidencias con una versión concreta.
- **Método**. Fijar el commit, probar ingreso por rol y el flujo sintético de telemetría, mapa, alertas y reportes, y registrar el resultado.
- **KPI y umbral**. Un recorrido ejecutado por una segunda persona y los resultados de todos sus pasos obligatorios.
- **Evidencia**. Guía, lista de verificación, versión y registro de pruebas.
- **Criterio de validez**. Cada paso indica versión, datos y entorno. Los fallos quedan registrados por prioridad.
- **Responsable / revisor**. Desarrollo / QA distinto de quien preparó el entorno.
- **Estimación**. 4–8 h de trabajo activo.

### H1-04 · Actualizar el contrato de API y validar la telemetría

- **Objetivo directo**. Alinear OpenAPI y Postman con la versión de evaluación y definir datos consistentes.
- **Justificación**. Hay diez operaciones ausentes del contrato guardado. La adaptación de una fuente necesita reglas de orden y duplicados.
- **Método**. Comparar el esquema generado, actualizar ejemplos, acordar identificadores y unidades, y verificar reenvíos y orden en un ensayo sintético.
- **KPI y umbral**. Cero diferencias sin justificar en el contrato de la API elegida y casos de orden y reintento con resultado documentado.
- **Evidencia**. OpenAPI, colección revisada, contrato de telemetría y resultados.
- **Criterio de validez**. Los ejemplos usan datos sintéticos y se reproducen contra la versión identificada.
- **Responsable / revisor**. Backend / QA distinto del autor.
- **Estimación**. 8–16 h de trabajo activo.

### H1-05 · Corregir y documentar la evaluación de minería

- **Objetivo directo**. Hacer reproducible la evaluación sintética de CRISP-DM.
- **Justificación**. El pipeline Python ajusta preprocesamiento antes de separar datos. Orange tiene un ensayo por lote independiente.
- **Método**. Instrumentar el flujo de entrenamiento y evaluación, ajustar los transformadores solo con entrenamiento y volver a reportar métricas.
- **KPI y umbral**. Un ensayo reproducible con partición registrada y dos referencias separadas para Python y Orange.
- **Evidencia**. Código, configuración, registro de partición y métricas.
- **Criterio de validez**. El revisor verifica que los datos de evaluación se reservaron y que ambos resultados se identifican como sintéticos.
- **Responsable / revisor**. Datos / revisor metodológico distinto del autor.
- **Estimación**. 6–12 h de trabajo activo.

### H1-06 · Revisar el agente de apoyo y la automatización

- **Objetivo directo**. Confirmar el alcance del agente y decidir qué integraciones requiere el piloto.
- **Justificación**. El laboratorio, el análisis por cola y la automatización externa producen evidencias diferentes.
- **Método**. Revisar los casos ya implementados, confirmar revisión humana y registrar los contratos e integraciones que se deben validar.
- **KPI y umbral**. Tres escenarios de laboratorio documentados y una decisión por cada integración propuesta para el piloto.
- **Evidencia**. Registro de casos, configuración y decisión de alcance.
- **Criterio de validez**. La evidencia registra origen del resultado y efecto de cada caso en el sistema.
- **Responsable / revisor**. Responsable de automatización / QA distinto de quien integra.
- **Estimación**. 4–8 h de trabajo activo.

### H1-07 · Cerrar los riesgos de operación que afectan al piloto

- **Objetivo directo**. Preparar la candidata para una instalación controlada.
- **Justificación**. La auditoría y los ensayos históricos dejan pendientes que dependen del entorno y de la versión.
- **Método**. Verificar vigencia de los hallazgos. Priorizar revisión defensiva de roles, concurrencia de administración, registros, recuperación, dependencias de red y carga. Ensayar en entorno autorizado.
- **KPI y umbral**. Todos los hallazgos críticos aplicables tienen resultado, corrección validada o bloqueo explícito antes del piloto.
- **Evidencia**. Matriz de QA, resultado de respaldo y restauración y registro de instalación.
- **Criterio de validez**. La revisión usa la candidata elegida y registra qué comprobaciones dependen del entorno real.
- **Responsable / revisor**. Infraestructura y QA / responsable de revisión distinto del ejecutor.
- **Estimación**. 8–16 h iniciales de trabajo activo.

### H4-01 · Validar el problema con usuarios y buscar un aliado

- **Objetivo directo**. Identificar un usuario inicial, quién decide y qué proceso se quiere mejorar.
- **Justificación**. La hipótesis de mercado puede contrastarse mientras se consiguen materiales.
- **Método**. Acordar guion, entrevistar perfiles de operación y decisión, y registrar necesidades, alternativas y candidatos a aliado.
- **KPI y umbral**. Una ronda documentada con cobertura de ambos perfiles y meta de entrevistas acordada por el equipo.
- **Evidencia**. Guion, notas anonimizadas, síntesis y decisión sobre segmento.
- **Criterio de validez**. Las conclusiones citan observaciones registradas y separan interés de compromiso con el piloto.
- **Responsable / revisor**. Validación de usuarios / asesor distinto del entrevistador.
- **Estimación**. 8–16 h iniciales de trabajo activo.

### H4-02 · Aclarar los derechos y las licencias con la universidad

- **Objetivo directo**. Obtener una decisión institucional sobre uso, transferencia y licencias.
- **Justificación**. El alcance comercial depende de la titularidad y de los permisos de código, modelos y datos.
- **Método**. Inventariar contribuciones y licencias, llevar las preguntas a la instancia institucional y documentar su respuesta.
- **KPI y umbral**. Una matriz de derechos y una revisión institucional registrada antes de definir una oferta.
- **Evidencia**. Inventario, acta o respuesta institucional y pendientes asignados.
- **Criterio de validez**. La respuesta identifica titulares, restricciones y decisiones requeridas para avanzar.
- **Responsable / revisor**. Líder del proyecto / instancia institucional o asesor distinto del responsable.
- **Estimación**. 4–8 h de preparación de trabajo activo.

### H4-03 · Validar el piloto con un usuario y medir el costo real

- **Objetivo directo**. Evaluar la utilidad del producto y los costos de instalarlo y mantenerlo.
- **Justificación**. El PDF académico y el Lean Canvas ofrecen supuestos que requieren evidencia de un piloto.
- **Método**. Acordar el proceso y línea base, ejecutar el piloto autorizado después de campo y medir uso, instalación, almacenamiento y soporte.
- **KPI y umbral**. Un informe con las métricas de utilidad acordadas y costos observados de instalación y operación.
- **Evidencia**. Acuerdo de piloto, registro de uso, informe y costos.
- **Criterio de validez**. El aliado revisa los resultados y el informe distingue costos observados de estimaciones.
- **Responsable / revisor**. Responsable del piloto / usuario designado y distinto del ejecutor.
- **Estimación**. 12–24 h de trabajo activo inicial de trabajo activo.

### H4-04 · Definir qué se puede ofrecer y en qué condiciones

- **Objetivo directo**. Preparar una oferta acorde con el desempeño y el servicio comprobados.
- **Justificación**. Una oferta necesita alcance verificable, costos y responsabilidades de soporte.
- **Método**. Revisar resultados de campo y piloto, calcular costos, acordar soporte y someter la oferta a decisión institucional.
- **KPI y umbral**. Una ficha de oferta revisada con alcance, límites, costos, soporte y decisión registrada.
- **Evidencia**. Ficha de producto, matriz de evidencia y acta de decisión.
- **Criterio de validez**. Cada capacidad ofertada se vincula a evidencia. La oferta cuenta con la revisión institucional correspondiente.
- **Responsable / revisor**. Líder de transferencia / instancia institucional distinta de quien prepara la ficha.
- **Estimación**. 6–12 h de trabajo activo.

## Cómo usar el tablero del CIAI Hub

1. En **Pendiente**, selecciona **Añadir una tarjeta**. Escribe el código y título, por ejemplo `H1-01 · Documentar la prueba simulada realizada`, y pulsa **Añadir tarjeta**. Si ya existe el código, edita la tarjeta.
2. Abre la tarjeta creada. Usa su descripción para pegar la ficha completa o registrar dónde está. Registra quién produce, quién revisa y dónde se añadirá la evidencia. Cuando el archivo se publique en GitHub, usa su enlace al apartado de la tarea.
3. Pasa la tarjeta a **En progreso** al empezar el trabajo. Si aparece un bloqueo, anota la causa, quién lo resuelve y cuándo lo revisarán.
4. Pásala a **En revisión** cuando estén disponibles el entregable y la evidencia. Si se requiere una corrección, vuelve a **En progreso** y deja anotado el ajuste.
5. Pásala a **Hecho** cuando la segunda persona confirme que se cumplieron el umbral de la tarea y el criterio de validez, y quede su revisión registrada. La aprobación del hito se registra al revisar su puerta de avance.

La pestaña **Tablero** muestra las tarjetas por estado. La pestaña **Tabla** permite revisarlas como lista. **Cronograma** permite revisar su distribución en el tiempo cuando tengan fechas. Empieza por reunir la evidencia existente en H1-01 y anota en H0-02 cuándo se revisará la disponibilidad de recursos para campo.
