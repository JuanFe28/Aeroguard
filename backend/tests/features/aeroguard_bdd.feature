# language: es
# Especificación para explicar BDD. No tiene step definitions ejecutables.
Característica: Verificar el monitoreo y la evidencia de AeroGuard
  Como equipo de monitoreo del prototipo académico
  Quiero validar detecciones, alertas y reportes
  Para explicar la fase TEST con criterios observables

  Antecedentes:
    Dado que AeroGuard está disponible en modo local
    Y que el usuario autorizado ha iniciado sesión

  Escenario: Analizar una imagen válida con el motor de visión disponible
    Dado un fotograma JPEG con un objeto oscuro sobre un fondo de cielo
    Cuando el operador lo envía a "/api/v1/ai/analyze"
    Entonces la API responde con código 200
    Y devuelve el nombre del motor utilizado
    Y devuelve un "bounding_box" con dimensiones positivas
    Y devuelve un nivel de confianza entre 0 y 1

  Escenario: Rechazar archivos que no sean imágenes
    Dado un archivo de texto con extensión ".txt"
    Cuando el operador lo envía a "/api/v1/ai/analyze"
    Entonces la API responde con código 400
    Y explica los formatos permitidos

  Escenario: Avisar de una incursión en geocerca con sonido habilitado
    Dado que el mapa muestra una zona restringida activa
    Y que el operador habilitó el sonido mediante un clic
    Cuando una detección ingresa en la geocerca
    Entonces aparece una alerta visual de incursión
    Y se solicita reproducir la alerta sonora en el navegador

  Escenario: Descargar un reporte PDF con huella de los datos
    Dado que el usuario tiene el permiso "reports:read"
    Cuando solicita "/api/v1/reports/export/pdf"
    Entonces recibe código 200 y tipo "application/pdf"
    Y recibe un documento que comienza con la firma "%PDF-"
    Y la cabecera "X-Report-SHA256" contiene 64 dígitos hexadecimales
    Y la huella corresponde a los datos del reporte según el contrato actual
