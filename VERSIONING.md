# Versionado de AeroGuard

Usamos SemVer con el formato MAYOR.MENOR.PARCHE. Un cambio incompatible incrementa MAYOR. Una función compatible incrementa MENOR. Una corrección compatible incrementa PARCHE.

La candidata académica actual es **1.2.0-rc.1** y su etiqueta Git es **v1.2.0-rc.1**. `rc` indica una candidata que se entrega para revisión. No significa que el prototipo ya esté validado para uso operativo. Python representa esta misma candidata como `1.2.0rc1` en `pyproject.toml`.

Cada publicación identifica el commit exacto y los digests SHA256 de sus cuatro imágenes. Una etiqueta publicada no se reutiliza para otro código. Si hace falta corregir la candidata se crea `1.2.0-rc.2`. La versión estable `1.2.0` se reserva para una aceptación posterior.

Pasos de Release

1. Revisar las pruebas y las dependencias del commit candidato.
2. Actualizar la versión y `CHANGELOG.md`.
3. Ejecutar `Release de AeroGuard en GHCR` desde GitHub Actions con la versión acordada.
4. Confirmar el resultado correcto de quality y de las cuatro publicaciones.
5. Verificar cada imagen en GHCR y guardar sus digests y las evidencias.
6. Crear la etiqueta Git y la prerelease en GitHub con sus notas.

GHCR conserva las imágenes backend, frontend, ai-service y simulator. Las credenciales se suministran mediante `GITHUB_TOKEN` y no se escriben en los archivos del proyecto. El usuario que inicia la ejecución aparece como actor y el paquete pertenece al espacio del repositorio compartido.

Release prepara e identifica un entregable. El despliegue de ese entregable en un servidor corresponde a la fase Deploy.
