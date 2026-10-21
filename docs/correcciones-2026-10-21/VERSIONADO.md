# Versionado y preparación para GitHub

Se adopta SemVer: MAJOR para cambios incompatibles de contrato, MINOR para funcionalidades compatibles y PATCH para correcciones. La identificación de trabajo pasa de 1.1.0 a **1.2.0** por persistencia de reportes, programación y observabilidad. Exigir autenticación en rutas antes abiertas se trata como corrección de seguridad; se documenta para actualizar clientes.

La identificación interna no crea una release. Mantener el apartado `Unreleased` hasta aceptar el commit, completar CI remoto y autorizar la publicación. Una candidata se etiqueta `v1.2.0-rc.1`; la versión estable requiere aceptación y un manifiesto que asocie commit y digests realmente publicados.

El trabajo se conserva en la rama `fix/release-readiness`, separado de `main`. El commit inicial `33ea70a` preservó la auditoría y los cambios locales previos, incluidas las dos eliminaciones que ya estaban en el workspace. El cierre incorpora código, configuración, pruebas y evidencia nueva.

Se prepara un bundle de todas las referencias Git, comprobado con `git bundle verify`, en `backups/`. No contiene `.env`, bases ni reportes privados; estos tienen un respaldo separado. Para enviar o actualizar esta rama se utiliza:

```powershell
git push --set-upstream origin fix/release-readiness
```

Después se puede abrir un PR hacia `main`, revisar Actions y aprobar el merge. No se ha forzado `main`, creado un tag oficial, publicado imágenes ni enviado mensajes a terceros. La ejecución local de Docker no demuestra que Actions haya corrido en GitHub.
