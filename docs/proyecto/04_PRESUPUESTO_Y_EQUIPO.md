# AeroGuard — Presupuesto y equipo (plantilla)

Versión: 10-11-2026. **Este documento es una plantilla.** Contiene la estructura que piden las convocatorias y los rubros que el proyecto necesita, pero **no contiene cifras**: el repositorio no tiene cotizaciones ni costos medidos, y un presupuesto inventado invalida una postulación. Cada `[ ]` debe completarlo el equipo con cotizaciones reales y las tarifas de la institución.

## 1. Equipo de trabajo

| Rol en el proyecto | Nombre | Formación / vinculación | Dedicación (horas/semana) | Responsabilidades |
|---|---|---|---|---|
| Director o investigador principal | `[ ]` | `[docente UTS / grupo de investigación]` | `[ ]` | Dirección científica, relación con la entidad financiadora |
| Líder técnico (backend e infraestructura) | `[ ]` | `[ ]` | `[ ]` | API, base de datos, despliegue, seguridad |
| Desarrollador de interfaz | `[ ]` | `[ ]` | `[ ]` | Consola web, mapas, accesibilidad |
| Responsable de IA y datos | `[ ]` | `[ ]` | `[ ]` | Captura y anotación, entrenamiento, evaluación |
| Responsable de calidad y operación | `[ ]` | `[ ]` | `[ ]` | Pruebas, monitoreo, respaldos, documentación |
| Responsable de validación con usuarios | `[ ]` | `[ ]` | `[ ]` | Entrevistas, piloto, modelo de negocio |
| Asesor jurídico (externo) | `[ ]` | `[ ]` | Por horas | Titularidad, licencia, datos personales, contrato de piloto |

Personas que figuran como autoras en el historial del repositorio y deben confirmarse en esta tabla: Juan Celis (`JuanFe28`), Alvino Camacho Bonna (`camachoab21-cmd`) y el Laboratorio de Inteligencia Artificial de las UTS.

**Anexos que suelen pedirse:** hoja de vida de cada integrante (CvLAC si la convocatoria es de MinCiencias), carta de compromiso y certificado de vinculación.

## 2. Presupuesto por rubros

Columnas habituales: valor solicitado a la entidad, contrapartida en dinero y contrapartida en especie.

| Rubro | Descripción y justificación | Cantidad | Valor unitario | Solicitado | Contrapartida dinero | Contrapartida especie |
|---|---|---|---|---|---|---|
| **Talento humano** | Dedicación del equipo de la tabla anterior durante 12 meses | `[ ]` | `[ ]` | `[ ]` | `[ ]` | `[ ]` |
| **Equipos: sensores** | Cámara óptica de exteriores para pruebas de detección visual | `[ ]` | `[ ]` | `[ ]` | | |
| **Equipos: sensores (opcional)** | Receptor de radiofrecuencia o radar de corto alcance, solo si el piloto lo requiere | `[ ]` | `[ ]` | `[ ]` | | |
| **Equipos: cómputo** | Estación con GPU para entrenamiento e inferencia | `[ ]` | `[ ]` | `[ ]` | | `[equipos del laboratorio]` |
| **Equipos: dron de pruebas** | Aeronave para generar datos de evaluación, operada por personal autorizado | `[ ]` | `[ ]` | `[ ]` | | |
| **Infraestructura** | Servidor o servicio en la nube para el piloto; almacenamiento de video | `[ ]` meses | `[ ]` | `[ ]` | | `[servidor institucional]` |
| **Software y licencias** | Licencias de modelos o bibliotecas si el uso comercial lo exige; herramientas de anotación | `[ ]` | `[ ]` | `[ ]` | | |
| **Servicios técnicos** | Anotación de imágenes; operador de dron autorizado; pruebas de seguridad externas | `[ ]` | `[ ]` | `[ ]` | | |
| **Asesoría jurídica** | Titularidad, licencia, datos personales y contrato de piloto | `[ ]` horas | `[ ]` | `[ ]` | | |
| **Propiedad intelectual** | Registro de software ante la DNDA; búsqueda y registro de marca ante la SIC | `[ ]` | `[ ]` | `[ ]` | | |
| **Salidas de campo** | Transporte y permisos para pruebas en el sitio del aliado | `[ ]` | `[ ]` | `[ ]` | | |
| **Divulgación** | Publicación, participación en evento, material de transferencia | `[ ]` | `[ ]` | `[ ]` | | |
| **Administración** | Porcentaje que fije la institución o la convocatoria | | | `[ ]` | | |
| **Total** | | | | `[ ]` | `[ ]` | `[ ]` |

### Cómo estimar cada rubro

- **Talento humano:** horas por semana × semanas × tarifa institucional. Es normalmente el rubro mayor.
- **Almacenamiento de video:** bytes por segundo × duración × número de cámaras × días de retención, más copias de respaldo.
- **Equipos:** tres cotizaciones por equipo, como exigen la mayoría de las entidades.
- **Contrapartida:** el tiempo de docentes, el uso de laboratorios y el servidor institucional suelen aceptarse como contrapartida en especie. Verificar el porcentaje mínimo que exige cada convocatoria.

## 3. Lo que el proyecto ya aporta

Sin valorar en dinero, el punto de partida incluye activos que se pueden declarar como antecedentes o contrapartida:

- Código fuente funcional de backend, interfaz, servicio de IA y simulador.
- Cuatro imágenes de contenedor publicadas y un procedimiento de despliegue probado.
- 167 pruebas de backend, 11 de frontend y 51 casos de navegador automatizados.
- Documentación técnica, comercial y normativa ([mapa](../README.md)).
- Uso del servidor privado donde se instaló la candidata `1.2.0-rc.1`.

## 4. Pendientes que bloquean una postulación

| Pendiente | Por qué importa | Responsable |
|---|---|---|
| Definir titularidad del software entre autores e institución | Sin ella no se puede firmar como proponente ni licenciar | `[ ]` |
| Elegir la licencia del código (hoy `UNLICENSED`) | Las convocatorias preguntan por la protección de resultados | `[ ]` |
| Aval institucional y vinculación a un grupo de investigación | Requisito habitual en convocatorias públicas | `[ ]` |
| Carta de intención de un aliado para el piloto | Suma puntaje y reduce el riesgo principal | `[ ]` |
| Cotizaciones de equipos | Sustentan el presupuesto | `[ ]` |
