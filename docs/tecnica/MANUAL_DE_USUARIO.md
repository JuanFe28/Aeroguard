# AeroGuard — Manual de usuario

Versión: 10-11-2026 · Código `1.2.0-rc.2`. Para quien usa la consola web. La instalación está en el [README](../../README.md) y la administración del servidor en el [manual de operación](../correcciones-2026-10-21/OPERACION.md).

## 1. Qué hace y qué no hace

AeroGuard muestra en un mapa los objetos aéreos que reportan los sensores registrados, avisa cuando uno entra en una zona restringida y guarda el registro de lo que el operador decidió.

AeroGuard **no** derriba ni interfiere drones, **no** identifica al piloto y **no** confirma por sí solo que un objeto sea un dron: la decisión es siempre de una persona. El análisis de imágenes es experimental.

## 2. Ingreso

1. Abrir la dirección de la consola en el navegador (en una instalación local, `http://localhost`).
2. Escribir usuario y contraseña y pulsar **Iniciar Sesión**.
3. Para salir, usar el botón de apagado en la esquina superior derecha. Al salir, la sesión queda revocada en el servidor.

**Olvidé mi contraseña:** el enlace «¿Olvidaste tu contraseña?» envía un correo con un enlace de un solo uso. Requiere que el administrador haya configurado el servidor de correo.

Tras varios intentos fallidos seguidos, el sistema bloquea temporalmente nuevos intentos.

## 3. Roles

| Rol | Para quién | Qué puede hacer |
|---|---|---|
| **Administrador** | Responsable del sistema | Todo: usuarios, sensores, zonas, configuración, detecciones, alertas, reportes y auditoría |
| **Operador** | Quien vigila en tiempo real | Ver el panel, registrar y actualizar detecciones, asignar y resolver alertas, consultar zonas e historial |
| **Analista** | Quien revisa después | Ver detecciones, alertas y zonas; generar reportes; consultar la auditoría y el historial |

Módulos visibles según el rol:

| Módulo | Administrador | Operador | Analista |
|---|---|---|---|
| Dashboard | ✔ | ✔ | ✔ |
| Detecciones | ✔ | ✔ | ✔ (solo lectura) |
| Alertas | ✔ | ✔ | ✔ (solo lectura) |
| Trayectorias | ✔ | ✔ | ✔ |
| Zonas Restringidas | ✔ (crea y edita) | ✔ (solo lectura) | ✔ (solo lectura) |
| Sensores | ✔ | — | — |
| Config. Detección | ✔ | — | — |
| Historial | ✔ | ✔ | ✔ |
| Reportes | ✔ | — | ✔ |
| Auditoría | ✔ | — | ✔ |
| Usuarios | ✔ | — | — |

## 4. Módulos

### Dashboard

Es la pantalla principal. Muestra:

- **Indicadores:** detecciones totales, activas, resueltas y alertas abiertas.
- **Mapa:** sensores, detecciones (coloreadas por nivel de amenaza) y zonas restringidas. Los marcadores se mueven solos cuando llega telemetría nueva.
- **Estado de conexión:** «En vivo» arriba a la derecha indica que el canal en tiempo real funciona. Si aparece «Reconectando», la consola sigue consultando los datos cada pocos segundos.
- **Alertas recientes, estado de sensores, perfil de altitud y dictamen del agente táctico** (experimental).
- **Sonido:** una sirena suena con alertas altas o críticas. Se puede silenciar con el botón «Sonido».

Si el mapa aparece vacío, es porque no hay sensores ni detecciones registradas todavía.

### Detecciones

Lista de objetos detectados con filtros. Permite ver el detalle, cambiar el estado (activa, pendiente, resuelta, descartada) y, según el rol, registrar una detección manual o enviar una imagen al análisis experimental.

### Alertas

Lista de alertas por severidad y estado. El flujo normal es:

1. La alerta aparece como **abierta**.
2. Un operador la **asigna**.
3. Al terminar, la **resuelve** escribiendo una nota obligatoria que explica qué pasó.

### Trayectorias

Muestra en el mapa y en una tabla el recorrido histórico de una detección. Si solo hay un punto, se muestra el punto sin inventar una ruta.

### Zonas Restringidas

Polígonos que el sistema vigila. Para crear una (administrador):

1. Pulsar **Nueva Zona** y completar nombre y rango de altitud. La zona queda como borrador inactivo.
2. Dibujar en el mapa al menos tres vértices.
3. Guardar el polígono. La zona queda activa.

Las zonas son las que define cada organización; no son cartografía oficial de la autoridad aeronáutica.

### Sensores (administrador)

Registro de los equipos que pueden enviar telemetría: nombre, tipo, posición, altitud y alcance. Un sensor debe estar registrado y activo para que el sistema acepte sus datos.

### Config. Detección (administrador)

Umbrales operativos (altitud y velocidades aceptadas) y activación del análisis experimental de IA.

### Historial

Consulta de eventos pasados.

### Reportes (administrador y analista)

Genera informes en PDF, Excel o CSV con filtros por periodo. Cada archivo lleva un hash SHA-256; al descargarlo de nuevo, el sistema verifica que no haya cambiado. También permite programar reportes periódicos.

### Auditoría (administrador y analista)

Registro de quién hizo qué y cuándo. El botón de verificación comprueba que la cadena de registros no haya sido alterada.

### Usuarios (administrador)

Alta de cuentas, asignación de rol y activación o desactivación. Si hay un error al guardar, el formulario conserva lo escrito.

### Perfil

Al pulsar el nombre de usuario se muestran los datos de la cuenta. Se cierra con la tecla Escape.

## 5. Tareas frecuentes

| Quiero… | Pasos |
|---|---|
| Atender una alerta | Alertas → abrir la alerta → Asignar → revisar la detección en el mapa → Resolver con nota |
| Ver por dónde pasó un objeto | Trayectorias → elegir la detección |
| Proteger un área nueva | Zonas Restringidas → Nueva Zona → dibujar → guardar |
| Entregar un informe | Reportes → elegir tipo, periodo y formato → Generar → Descargar |
| Dar acceso a una persona | Usuarios → Nuevo Usuario → elegir rol |
| Conectar un equipo nuevo | Sensores → Nuevo Sensor → activarlo; luego configurar el equipo para enviar telemetría con ese nombre |

## 6. Problemas comunes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El mapa se ve gris o sin calles | Sin conexión a Internet, o una versión antigua de la página en caché | Comprobar la conexión y recargar con Ctrl+F5 |
| El mapa no muestra nada moviéndose | No hay sensores enviando telemetría | Verificar que el sensor esté registrado, activo y transmitiendo; en una demostración, iniciar el simulador |
| Dice «Reconectando» | Se perdió el canal en tiempo real | Esperar; se reconecta solo. Si persiste, avisar al administrador |
| «Sesión expirada» | El token venció o la cuenta fue desactivada | Iniciar sesión de nuevo |
| No veo un módulo | El rol no tiene ese permiso | Pedirlo al administrador |
| No llega el correo de recuperación | El servidor de correo no está configurado | Pedir al administrador que restablezca la contraseña |
| No suena la sirena | El navegador bloquea el audio hasta que haya una interacción | Hacer clic en la página y revisar el botón «Sonido» |

## 7. Buenas prácticas

- Cada persona usa su propia cuenta; no compartir contraseñas.
- Escribir notas claras al resolver alertas: son la evidencia de la decisión.
- Tratar toda detección como un aviso que debe verificarse, no como una confirmación.
- Cerrar sesión al dejar el puesto.
