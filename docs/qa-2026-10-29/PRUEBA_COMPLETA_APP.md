# Batería de la aplicación después de configurar el servidor

Ensayo final local: **51 casos aprobados**, con 38 capturas/inventarios, once análisis de accesibilidad y comprobación de excepciones JavaScript en todos los casos. Resultado saneado y hashes del código ensayado: [RESULTADO_QA_INTERFAZ.json](RESULTADO_QA_INTERFAZ.json). Tres pruebas adicionales verifican que un informe vacío, parcial, fallido u omitido no se dé por aprobado. Las 175 regresiones existentes de backend y las diez del frontend siguen aprobadas; siete comprobaciones locales de Compose se omiten por falta de esa CLI.

El paso 5 de [COMANDOS_SERVIDOR_CASA.txt](../../COMANDOS_SERVIDOR_CASA.txt) arranca el código nuevo en QA y, si salud/despliegue pasan, llama a `scripts/run_server_app_qa.py`. Este valida proyecto y puerto de QA, construye Chromium con dependencias fijadas y ejecuta Playwright. No requiere instalar Node ni navegador en el servidor. La primera ejecución descarga imágenes y depende de Internet/CDN; comprobar memoria disponible antes de iniciar. No detener producción para obtener recursos.

El runner rechaza una versión que no contenga `-qa.`. Crea usuarios persistidos por rol con contraseñas aleatorias, obtiene sesiones mediante login real y prepara datos sintéticos. Las operaciones escriben únicamente en el stack aislado de QA; no restauran ni borran la BD de producción. Las ejecuciones usan prefijos nuevos y mantienen la evidencia anterior. El resultado de SQLite local no acredita PostgreSQL: la misma batería, ejecutada en ese stack, sí ejercita sus API y su BD PostgreSQL reales.

## Cobertura automática preparada

| Módulo | Campos / controles ejercitados | Resultado comprobado |
|---|---|---|
| Login | Usuario, contraseña, mostrar/ocultar, enviar, olvidé contraseña, correo vacío y volver | Obligatorios, contraseña corta, transición, entrada con credenciales reales |
| Restablecimiento | Nueva contraseña, confirmación, enviar sin token válido | Error visible y ausencia de cambio; entrega SMTP/enlace real pendiente |
| Navegación | Enlaces de los once módulos, campana, perfil por teclado/Escape, sidebar, salir/cancelar/confirmar | Destino correcto, identidad real, apertura/cierre, retorno a login |
| Dashboard | Capas zonas/sensores, centrar/ajustar, sonido, sirena, SOAR experimental, historial | Cambio de estado de controles, mapa disponible y respuesta del análisis; sonido físico no verificable en Chromium sin interfaz |
| Sensores | Nombre, tipo, latitud, longitud, altitud, alcance, cancelar/cerrar/guardar, actualizar, activar/desactivar, editar | Obligatorios, latitud inválida, coordenadas cero, persistencia y conservación de estado |
| Usuarios | Nombre/apellido con tildes/ñ, usuario, correo, rol, contraseña inicial, buscar, crear/editar, estados, cancelar/cerrar | Persistencia, usuario de edición solo lectura, cambio de rol y estados |
| Zonas | Nombre, descripción, severidad, mínimo/máximo, mapa, ubicaciones, crear/cancelar/cerrar, dibujar/guardar polígono, editar/activar/desactivar/eliminar | Rango inválido conserva formulario, borrador, tres clics reales, persistencia y eliminación solo del registro sintético propio |
| Detecciones/IA | Búsqueda, filtros, actualizar, sensor real, muestra sintética, inferencia, cerrar modal, fila de detección | Estado vacío, filtro, respuesta del motor, enlace válido a trayectoria; no valida precisión sobre vuelos reales |
| Trayectorias | Actualizar, selector, cargar, cambio de selección | Tres puntos recibidos, tabla visible y limpieza al cambiar |
| Alertas | Filtros estado/severidad, actualizar, asignar, resolver/cancelar/confirmar | Cambios reales en la API y estado resuelto de la alerta sintética |
| Reportes | Cuatro fechas, cinco botones de descarga, programación: nombre/cron/formato/guardar/eliminar | Descarga PDF/CSV/Excel y persistencia/eliminación de programación sintética |
| Historial/auditoría | Descargas CSV/Excel, lectura de auditoría y API de verificación | Archivo descargado, eventos de login visibles y cadena válida |
| Permisos | Admin, operador, analista, anónimo; enlaces y navegación directa | Secciones restringidas ausentes/redirigidas, API con 401/403 |
| Presentación | Once pantallas a 1440×1000, 768×1024 y 390×844 | Captura completa, título, texto sin caracteres corruptos/undefined, paleta, desbordamiento horizontal; contraste y reglas WCAG con axe en escritorio |

El inventario adjunto registra cada botón, enlace, input, selector y textarea visible: ID, etiqueta, tipo, obligatoriedad, límites, color, fondo y tipografía. **Inventariado no significa ejercitado en todos sus estados.** Esta matriz describe las acciones explícitas; controles dinámicos de terceros, todas las combinaciones de datos y estados de error no se declaran cubiertos al 100 %. La carga WebSocket, reglas de backend y scheduler conservan sus baterías separadas.

## Informe y criterio de aceptación

En el servidor se crea `backups/qa-app-FECHA/`, excluido de Git. El TXT incluye cómo descargar esa carpeta al portátil:

- `html/index.html`: informe de cada caso con errores, inventarios y capturas.
- `results.json`: resultados originales del runner.
- `RESUMEN.json`: aprobación automática y fallos; la aceptación visual siempre inicia pendiente.
- `REVISION_VISUAL.html`: galería para revisar letras, tildes, textos, color, contraste, alineación, espacios, recortes, tablas/mapas y presentación en los tres tamaños.

Una prueba fallida devuelve código distinto de cero y detiene la aceptación del paso 5. No actualizar producción hasta resolverla o registrar expresamente su limitación y decisión de aceptación. Las capturas contienen datos de QA y los errores del runner podrían incluir credenciales sintéticas; conservar toda la carpeta en privado, sin subirla a GitHub ni copiarla al chat sin sanear.

Las capturas no se comparan contra un diseño aprobado porque todavía no existe esa referencia. La primera revisión humana debe registrar fecha, SHA, navegador, tamaño, observaciones y aprobación por pantalla. Para añadir comparación de píxeles posteriormente se necesitan referencias aceptadas en el mismo sistema/navegador; no crear una referencia y declararla aprobada automáticamente. [Documentación de comparación visual de Playwright](https://playwright.dev/docs/test-snapshots).

## Ensayo antes de llegar a casa

`scripts/run_local_app_qa.py` levanta una instancia efímera con SQLite, credenciales nuevas y frontend del mismo checkout; después ejecuta exactamente los mismos casos de navegador y termina su servidor. Usa Node 24, `npm ci` y `npx playwright install chromium`. Las verificaciones de PR repiten este ensayo en Linux y validan el Compose del runner; no configuran el servidor doméstico.

El montaje Docker y PostgreSQL del destino, SMTP, receptor de notificaciones, sonido físico, sensores/imagen real y aceptación humana permanecen sujetos a su prueba específica. Continuar con [ACEPTACION_SERVIDOR.md](ACEPTACION_SERVIDOR.md) y registrar Trello con las evidencias de cada tarjeta.
