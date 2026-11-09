# Trayectorias y autoridades aplicables en Colombia

Revisión: 29 de octubre de 2026. Alcance: prototipo académico AeroGuard. La aplicabilidad depende de la actividad real, el equipo instalado, los datos y el cliente; este documento no acredita permisos ni certifica cumplimiento.

## Hallazgos de trayectorias y correcciones locales

La vista anterior solo ofrecía un selector y una línea con cuatro estadísticas. No explicaba la ausencia de detecciones ni distinguía una única muestra de un recorrido; conservaba la ruta anterior al fallar otra consulta. El selector esperaba `timestamp` y `sensor_name`, aunque la respuesta puede entregar `created_at` y `sensor_id`. La capa CARTO presentaba el mismo problema de clave observado en Zonas.

Se añadieron estados vacíos y de error, actualización del selector, tabla cronológica con coordenadas/altitud/velocidad/rumbo, etiquetas de inicio/fin, manejo de una única muestra y limpieza de la ruta al cambiar la selección. Una respuesta atrasada no puede reemplazar otra selección. El mapa usa OSM con atribución. La consulta muestra hasta 50 detecciones recientes; la paginación histórica sigue pendiente.

La API de trayectoria ahora distingue ID mal formado (422), detección inexistente (404) y detección existente sin muestras (lista vacía). Ordena por fecha, secuencia e ID. La ingesta conserva la fecha enviada por el sensor, normalizada a UTC; si falta usa la recepción, y si llega sin zona horaria se interpreta como UTC. Esto no valida la sincronización del reloj del sensor.

Pruebas: **118 pruebas funcionales aprobadas, 7 omitidas por falta de Docker Compose**, y **10 de frontend aprobadas**. Dos regresiones nuevas verifican existencia/UUID y conservación/orden temporal de tres paquetes del mismo objeto. Tres regresiones frontend cubren error tras otra ruta, muestra única y respuesta tardía. En navegador se comprobó primero la ausencia de detecciones y luego tres muestras sintéticas de QA: 0,16 km horizontales, promedio de muestras 16 km/h y altitud máxima 50 m. [Captura](trayectoria-sintetica.png).

Límites que permanecen:

- Es consulta histórica 2D con detalle altimétrico; no hay reproducción temporal, gráfico de altitud ni escena 3D.
- Hace falta `object_id` estable por sensor para acumular un seguimiento. Sin él, la ingesta puede generar detecciones separadas. No hay fusión entre sensores ni identificación física validada.
- No se demostró idempotencia de paquetes, sincronización de relojes ni tratamiento completo de saltos, intervalos sin cobertura o muestras concurrentes. Una línea entre puntos no demuestra observación continua del segmento.
- La velocidad usa la convención km/h de la interfaz; cada integración de sensor debe documentar y comprobar sus unidades. No se calcula velocidad física a partir del tiempo y distancia.
- La altitud no identifica por sí sola su referencia vertical (AGL/MSL) ni precisión. Falta ese contrato con cada sensor antes de comparar contra un límite aeronáutico.
- La asociación por sensor/objeto no acredita matrícula, fabricante, piloto, autorización o intención.

## Entidades y relación con las acciones

| Entidad | Ámbito | Relación con AeroGuard |
|---|---|---|
| Aeronáutica Civil — Aerocivil | Normativa aeronáutica y operación UAS bajo RAC 100 | Aplica al organizar vuelos y evaluar restricciones operacionales. Dibujar una geocerca no la convierte en restricción oficial ni determina por sí solo una infracción. |
| Ministerio TIC y Agencia Nacional del Espectro — ANE | MinTIC: permisos de espectro y régimen de inhibidores. ANE: vigilancia/control del espectro y competencias técnicas | Revisar al incorporar radar activo, transmisores u otros equipos RF. La detección pasiva y la interferencia son actividades distintas. La instalación de un sensor en el catálogo del programa no equivale a autorización de uso del espectro. |
| Superintendencia de Industria y Comercio — SIC | Protección de datos personales | Usuarios, imágenes y trayectorias asociables a personas exigen evaluar finalidad, base jurídica, accesos, retención y destinatarios. Una ruta de un objeto que no permite identificar personas no se convierte automáticamente en dato personal por ser una coordenada. |
| Superintendencia de Vigilancia y Seguridad Privada | Control de servicios de vigilancia privada y régimen de equipos/medios tecnológicos | Si se comercializa, instala u opera como solución o servicio de vigilancia, revisar clasificación, registros y licencias correspondientes. No se ha determinado que la licencia de software aislada tenga el mismo tratamiento que prestar el servicio completo. |

Fuentes oficiales consultadas:

1. Texto de Aerocivil, **RAC 100**, alojado en el [registro estatal SUIT](https://tramites1.suit.gov.co/registro-web/suit_descargar_archivo?A=130309): identifica la adopción mediante Resolución 01983 de 2023. El portal directo de Aerocivil devolvió 403 y la descarga SUIT no pudo completarse; el índice de búsqueda permitió identificar el documento. **No se certificó la edición consolidada vigente ni se extrajeron límites operacionales específicos.** Confirmar la última edición y restricciones oficiales antes de vuelos de prueba.
2. [MinTIC, Resolución 2774 de 2013, texto con anotaciones](https://normograma.mintic.gov.co/mintic/compilacion/docs/resolucion_mintic_2774_2013.htm), arts. 3–5: prohibición general de inhibidores salvo eventos autorizados; el art. 5, modificado en 2018, contempla casos especiales para organismos de seguridad del Estado y ANE. No es una autorización para usuarios particulares de AeroGuard.
3. [SIC, concepto 23281341](https://sedeelectronica.sic.gov.co/sites/default/files/boletin-juridico/conceptos/23281341.pdf): imágenes de personas identificadas o identificables y tratamiento bajo Ley 1581 de 2012. El índice permitió consultar el contenido; no se presume obligación universal de registrar toda base en RNBD.
4. [Supervigilancia, preguntas frecuentes](https://www.supervigilancia.gov.co/preguntas-frecuentes-supervigilancia): inspección, vigilancia y control, y licencia para prestación de servicios. Véanse también sus [conceptos sobre medios tecnológicos](https://supervigilancia.gov.co/loader.php?idFile=159&lFuncion=exposeDocument&lServicio=Tools2&lTipo=descargas), con referencia a los arts. 52–53 del Decreto Ley 356 de 1994. Revisar clasificación concreta antes de oferta o piloto comercial.
5. Para un uso de aviación de Estado, consultar además la [Autoridad Aeronáutica de Aviación de Estado](https://aaaes.devfac.mil.co/), que publica su marco RACAE; no trasladar requisitos civiles automáticamente a una operación estatal.

## Acciones del programa y decisiones que faltan

El código consultado registra telemetría, reconstruye rutas, compara geocercas configuradas, genera alertas/reportes y ejecuta reglas locales o despacha un webhook n8n si está configurado. No se comprobó hardware de inhibición ni neutralización. Un dictamen de reglas o IA no concede facultades policiales, aeronáuticas o de interferencia.

Antes de uso real deben definirse:

- Fuente, fecha, autoridad, vigencia y referencia vertical de cada geocerca; diferenciar polígonos del cliente, ejemplos académicos y áreas oficiales.
- Etiqueta «coincidencia con regla configurada» en lugar de declarar automáticamente «vuelo ilegal» o «dron hostil».
- Revisión humana antes de escalar y un protocolo del sitio que determine destinatario y canal autorizado; no programar avisos oficiales sin un acuerdo de integración.
- Política de retención/acceso a trayectorias e imágenes y evaluación de lo enviado a terceros (n8n, correo, nube o modelos).
- Responsabilidad del operador, validación de sensores, reloj, unidades y precisión. Los ejemplos de 120 m del dashboard no son una validación jurídica de todos los vuelos.

Estos son requisitos propuestos a partir de la revisión técnica y las fuentes, no certificaciones obtenidas por el proyecto. No se publicaron cambios ni se operó el servidor privado.
