# Resultados de Test para Trello

Fecha: 19 de octubre de 2026, America/Bogota. Resultados del código local corregido.

| Tarjeta | Resultado observado | Estado para el alcance probado |
|---|---|---|
| TEST-01 | 64/64 pruebas, 0 fallos; cobertura de líneas 70,21 % | Aprobada, con porcentaje medido |
| TEST-02 | 3/3 escenarios, 10/50/100 clientes; P95 a 100 = 50.861 ms; cero pérdidas | Aprobada para carga local acotada |
| TEST-03 | Bandit: 0 altos, 0 medios y 17 bajos revisados; 23 regresiones aprobadas | Completada con observaciones documentadas |

Las 23 regresiones ya están incluidas en las 64 pruebas: en total se ejecutaron **67 casos**, no 90. Los detalles están en `evidencias/CASOS_EJECUTADOS.md` y los archivos `TRELLO_TEST_01.md`, `TRELLO_TEST_02.md`, `TRELLO_TEST_03.md`.

Se corrigieron accesos indebidos por tokens demo, cuentas eliminadas/desactivadas, tipos de token incorrectos en WebSockets, sobrescritura de reportes, el comprobador de disponibilidad y manejadores de errores. Las pruebas del login real, demo local, exportaciones y roles siguen aprobando.

Los criterios son los alcances descritos en los informes: el JSON de Trello no incluía descripción ni criterios de aceptación. Un umbral de cobertura superior o cero avisos bajos requeriría satisfacer ese criterio adicional. Los procesos de demostración ya abiertos necesitan reiniciarse para cargar los cambios guardados; la verificación final importó el código corregido en procesos de prueba nuevos. No se modificó Trello automáticamente.

El ZIP general incluye resultados finales, reportes de cobertura y resúmenes de fallos previos sin trazas completas. La comprobación de seguridad es SAST del código Python indicado, no una garantía de ausencia de vulnerabilidades en todo el producto.
