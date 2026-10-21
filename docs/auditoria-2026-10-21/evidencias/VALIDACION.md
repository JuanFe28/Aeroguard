# Registro de validación de cierre

Fecha: 21-10-2026, America/Bogota.

- `baseline/`: base 28c955f reproducida; las 13 sondas iniciales produjeron 12 fallos y 1 control positivo antes de corregir comportamiento.
- `final/`: intento intermedio fallido, conservado para trazabilidad; no es un resultado de aprobación. La traza extensa permanece en `tmp/audit/intento-intermedio-pytest.txt` y aquí se conserva resumen y XML.
- `verificado/`: primera ejecución aprobada, 77 funcionales + 3 carga, antes de ampliar a los dos casos de carga/formato.
- **`cierre/`: ejecución definitiva de comportamiento, 79 funcionales + 3 carga, 72,28 % de cobertura de líneas.** SAST sin medios/altos; 23 bajos descritos en informe 1. El resultado `checks_passed=true` no incluye el escaneo de dependencias, que se ejecutó aparte y tiene avisos abiertos.
- `selenium-cierre*`: última verificación visual/funcional demo, con rótulo de datos simulados, sin ventana ni perfil del usuario. No es un E2E con sensores reales.
- `openapi-actual.json`: regenerado después de aclarar las descripciones de IA/reportes. Estos últimos cambios fueron de metadatos/documentación, sin cambiar comportamiento. Sintaxis Python y configuración Compose comprobadas de nuevo.
- Los ajustes del Dockerfile posteriores a la suite solo completan el empaquetado de bibliotecas y archivos necesarios en la etapa test. **No hubo build Docker**, y no se atribuye a las pruebas locales un resultado sobre esas imágenes.
- `baseline/dependencias.json`: respuesta de pip-audit 2.9.0 para el entorno instalado. 65 avisos en 11 paquetes; el informe puede incluir aliases y no acredita explotación. `triaje-dependencias.csv` distingue 8 paquetes runtime (54 avisos) de 3 herramientas (11 avisos). No se actualizaron los requisitos para forzar un resultado limpio.
- `entorno-instalado.txt`: versiones resueltas de este entorno, incluyendo herramientas de auditoría; `pip check` sin dependencias rotas. No equivale a un lock ni a SBOM de contenedores.
- `manifiesto-fuentes.json`: hashes del árbol local al concluir la revisión. Las eliminaciones locales previas continúan presentes; los resultados no se atribuyen a un commit nuevo inexistente.

Controles pendientes: build y smoke de contenedores; PostgreSQL/PostGIS; RabbitMQ/n8n; colección Postman y runner BDD; pruebas de campo de visión; restauración de backup; ejecución de CI en GitHub; aceptación docente y publicación autorizada. No se emitió certificación ni se publicó un Release.
