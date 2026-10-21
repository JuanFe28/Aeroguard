# Informe 3 — Investigación comercial preliminar

Consulta: **21-10-2026**. Estudio documental, inicialmente Colombia. Se separan afirmaciones de fabricantes, evidencia institucional e hipótesis propias. No hay entrevistas ni compradores validados. Fuentes y límites de acceso en [06_FUENTES.md](06_FUENTES.md).

## Problema y señal local de necesidad

La necesidad operativa es recibir observaciones de objetos, verificar su origen, priorizar incidentes y coordinar una respuesta humana con trazabilidad. Una alarma equivocada puede consumir recursos y una omisión puede dejar un incidente sin atender; AeroGuard todavía no mide ninguno de esos costos.

Hay una señal colombiana verificable más concreta que una estimación de mercado global: CODALTEC publicó en 2026 requerimientos de interfaz e integración C-UAS (020-2026, abril) y de prueba de concepto radar para aeronaves no tripuladas (044-2026, junio). Son antecedentes de demanda institucional especializada, no compras confirmadas para AeroGuard ni convocatorias que deban considerarse abiertas hoy. La página mezcla estados visuales y fechas vencidas. [Convocatorias oficiales CODALTEC](https://codaltec.com/convocatorias-y-recepcion-de-ofertas/).

La autoridad aeronáutica publica restricciones y zonas UAS, y recomienda coordinación para tecnologías antidrones. Esto confirma un contexto regulado; no demuestra presupuesto disponible en todos los aeropuertos. [Información oficial Aerocivil](https://www.aerocivil.gov.co/prensa/noticias/Pages/Informacion-importante-sobre-la-regulacion-de-la-aviacion-no-tripulada-UAS.aspx).

## Segmentos que conviene validar

La prioridad siguiente es una hipótesis de accesibilidad y riesgo, no una medición de capacidad de compra.

| Segmento en Colombia | Necesidad a contrastar | Comprador / presupuesto por verificar | Barreras | Prioridad propuesta |
|---|---|---|---|---|
| Universidades y centros de formación | Entrenamiento, simulación y evaluación de protocolos | Director de laboratorio / programa | Titularidad del proyecto, costo de soporte | Alta para uso académico aislado |
| Integradores de seguridad y centros de operaciones | Unificar eventos y reducir trabajo manual | Director técnico / líder de operaciones | Acceso legal a APIs y equipos; responsabilidad | Alta para entrevistas e integración supervisada |
| Instalaciones industriales / centros logísticos | Saber si existe un incidente y quién debe verificarlo | Jefe de seguridad y administrador del sitio | Necesidad de sensores, cobertura, privacidad, presupuesto incierto | Media, piloto de alcance pequeño |
| Organizadores de eventos | Conciencia situacional temporal | Coordinador de seguridad / proveedor contratado | Despliegue temporal, permisos y falsos positivos | Media después de validación técnica |
| Aeropuertos / infraestructura crítica | Seguridad operacional y respuesta coordinada | Operador, concesionario o autoridad competente | Exigencia técnica alta, contratación y coordinación institucional | Baja como primer cliente de un prototipo |
| Defensa / entidades públicas | Integración y capacidades especializadas | Área técnica y contratación | Elegibilidad, interoperabilidad, contratación, autorizaciones | Exploración mediante aliado, sin oferta actual |

La contratación pública puede investigarse en [SECOP y datos abiertos de Colombia Compra Eficiente](https://operaciones.colombiacompra.gov.co/datos-abiertos). No se extrajo una base de contratos ni se calcularon ventas o precios a partir de ella.

## Qué se está comparando

**Detección:** observar la posible presencia de un objeto. **Identificación:** inferir tipo/identidad con evidencia. **Seguimiento:** asociar observaciones de un mismo objeto a lo largo del tiempo. **Neutralización:** intervenir para detenerlo. AeroGuard muestra eventos y geocercas y ofrece visión experimental; no demuestra identificación, seguimiento físico ni neutralización.

## Matriz competitiva

Las capacidades siguientes son declaraciones de las páginas oficiales, no resultados de ensayos independientes. País indica origen/sede documentada, no disponibilidad contractual en Colombia. No se verificó distribución local.

| Empresa / producto | País y mercados documentados | Público / tecnología / componentes | Integraciones y oferta comercial | Fortalezas / límites de comparación |
|---|---|---|---|---|
| Dedrone by Axon / DedroneTracker.AI | Grupo Axon, EE. UU.; oferta internacional de seguridad aérea. Adquisición completada anunciada en octubre de 2024 | Seguridad pública e instalaciones; software y sensores RF, radar, video y acústica | Fusión multisensor y conexión de respuestas según legalidad. Sin tarifa numérica encontrada en la página consultada | Plataforma e historial de sensores especializados; requiere equipos y condiciones de instalación. No se auditó exactitud ni costo total. [Producto](https://www.dedrone.com/products/drone-detection-software), [adquisición](https://www.axon.com/blog/axon-completes-acquisition-of-dedrone) |
| DroneShield / DroneSentry-C2 | Compañía australiana, presencia declarada también en EE. UU. y Países Bajos; mercado internacional | Defensa, policía e infraestructura; C2 con RF, radar y óptica | API REST, sensores propios y terceros; nube o servidor local, licencias y actualizaciones. Sin tarifa numérica pública localizada | Interoperabilidad y varias modalidades; dependencia de hardware y operación especializada. No se supone alcance universal. [Software](https://www.droneshield.com/products-software), [empresa](https://www.droneshield.com/) |
| Fortem / SkyDome Manager y TrueView | EE. UU., Utah; oferta internacional | Seguridad de espacio aéreo; radar 3D, cámaras y plataforma C2; DroneHunter es una familia de interceptores separada | Correlación de sensores y control de su ecosistema; cotización por configuración, sin precio numérico encontrado | Detección y seguimiento basados en sensores físicos; despliegue y costos por proyecto. Sus interceptores no son una función comparable a AeroGuard. [Sistema](https://fortemtech.com/products/), [sede](https://fortemtech.com/policies/terms-of-use/) |
| Aaronia / AARTOS | Alemania, Strickscheid; oferta de detección promovida internacionalmente, disponibilidad en Colombia no verificada | Recepción y análisis RF con sensores/antenas y software de espectro | Documentación oficial de protocolo JSON para AARTOS. Sin tarifa numérica localizada | Especialización RF; depende de emisiones observables y de configuración. Documentación de API antigua: confirmar versión y soporte comercial antes de elegirla. [Producto, ficha indexada](https://downloads.aaronia.com/datasheets/solutions/drone_detection/Aaronia_AARTOS_Drone_Detection_System.pdf), [protocolo](https://v6-forum.aaronia.de/forum/topic/rtsa-suite-pro-json-protocol/) |

No se asignan puntuaciones arbitrarias de precisión, alcance, precio o superioridad. La ausencia de información de precios significa que hace falta cotizar, no que el producto sea gratuito ni inaccesible. La referencia local a CODALTEC muestra además que no se debe asumir ausencia de capacidades nacionales.

## Brecha de AeroGuard frente a estas ofertas

| Capacidad | AeroGuard hoy | Brecha para una oferta comparable | Diferenciación a validar |
|---|---|---|---|
| Consola, eventos y roles | Prototipo y demo disponibles | Contratos consistentes, origen verificable y persistencia | Flujo sencillo en español y soporte local |
| Sensores reales | No integrados ni ensayados | Acuerdo de API y adaptador a un equipo real | Integración de equipos existentes del cliente |
| Fusión y tracking | Sin motor validado | Identidad temporal, sincronización y manejo de incertidumbre | Solo desarrollar si el piloto lo necesita |
| Visión de drones | Heurísticas sin métricas | Dataset, modelo específico y evaluación ciega | Validación con condiciones locales, si hay demanda |
| Reportes | Archivos reales con datos sintéticos | BD, filtros, recuperación por ID y trazabilidad de evidencia | Resumen operativo útil para supervisores |
| Operación | Herramientas de laboratorio | Seguridad, despliegue reproducible, backup y soporte | Implementación local con datos bajo control del cliente |

El mapa, un webhook o una interfaz en español son características replicables. No son todavía una ventaja defendible. La defensa competitiva requeriría acceso legítimo a datos, integraciones mantenidas, calidad demostrada y relaciones de servicio; ninguna está acreditada aún.

## FODA

| Fortalezas internas | Debilidades internas |
|---|---|
| Código disponible, pruebas y evidencia; API, roles y UI ya construidos; bajo costo inicial para aprender en laboratorio | Detección no validada; mocks mezclados con servicios; deuda de seguridad y dependencias; integración y soporte incompletos |
| Oportunidades externas — hipótesis | Amenazas externas |
| Formación, pilotos supervisados e integración de eventos donde una solución completa no sea necesaria | Proveedores especializados con hardware y canales; costo de falsos positivos; barreras de acceso a equipos y datos; responsabilidad y contratación |

## Posicionamiento y modelo económico propuestos

Evaluar primero **una plataforma de gestión y entrenamiento de eventos aéreos e integración supervisada**, para un integrador o laboratorio. La promesa inicial sería ordenar observaciones y decisiones humanas. No ofrecer detección universal ni seguridad garantizada.

- **Implementación local + mantenimiento:** plausible cuando el sitio necesita control de imágenes y conectividad limitada. Requiere instalación, actualizaciones y soporte con costo explícito.
- **Modelo híbrido:** procesamiento de video en sitio y envío de metadatos, si el cliente y la evaluación de privacidad lo permiten.
- **SaaS:** evaluar después de medir volumen, segregación entre clientes, conectividad y base legal. No trasladar video a la nube por defecto.
- **Licencia académica / formación:** posibilidad de validación temprana; revisar derechos del equipo y de la institución antes de comercializar.

No hay costos medidos ni cotizaciones. Modelo de costos a completar: `equipo/sensores + instalación + cómputo + almacenamiento + conectividad + licencias + horas de soporte + validación + seguros/asesoría`. Video domina almacenamiento y transferencia: bytes por segundo × duración × cámaras × retención, más copias y redundancia. Medir recursos por flujo y costo de soporte por sitio antes de definir precios. No se propone una tarifa sin esa información.

## TAM, SAM y SOM

No existe información suficiente para calcular cifras defendibles. No usar el valor mundial de C-UAS como TAM de AeroGuard ni equiparar todos los aeropuertos con clientes accesibles.

- **TAM:** sitios del segmento elegido que realmente necesitan esa función × gasto anual comparable verificable.
- **SAM:** subconjunto con equipos integrables, condiciones legales, canal y despliegue que AeroGuard pueda atender.
- **SOM:** clientes calificables y contratables dentro de la capacidad real de venta/instalación/soporte; no un porcentaje arbitrario del TAM.

Se necesitan inventario depurado de organizaciones/sitios, evidencia de problema, cotizaciones, frecuencia de incidentes, ciclo de compra y capacidad de soporte. Evitar contar una sede, una empresa y su integrador como tres compras del mismo sistema.

## Validación comercial y aliados posibles

Recomendación: 8–12 entrevistas exploratorias con operadores, integradores y responsables de compra, sin presentarlas como realizadas. Preguntar por incidentes recientes, tratamiento actual, equipos, tiempo de respuesta, falsos avisos, permisos, presupuesto y quién acepta el riesgo. Buscar un piloto pagado o una carta de interés con alcance y presupuesto; una opinión favorable no valida disposición de pago.

Aliados a explorar: laboratorios universitarios, integradores de videovigilancia, fabricantes con API documentada y asesores en privacidad/aviación. No hay acuerdos existentes ni autorización para contactar a ninguno. Primero demostrar un caso en Colombia; Latinoamérica exige revisión país por país y un socio de soporte. Internacionalización solo tras un piloto repetible y revisión de licencias y restricciones aplicables.

**Viabilidad preliminar:** merece validación como software de gestión/integración. No hay evidencia suficiente para un lanzamiento comercial como detector de drones. El siguiente hito es escoger un usuario y una fuente real, medir el problema y definir un piloto humano supervisado con límites claros.
