# Protocolos Operativos Defensivos C-UAS — AeroGuard

## 1. Marco de Supervisión y Restricciones Legales
- AeroGuard es una plataforma de **vigilancia, trazabilidad y apoyo a decisiones** para operadores de seguridad.
- La cota civil de referencia en operaciones estándar (alineada con RAC 100 Colombia como guía operativa) es de **120 m AGL (400 pies)** salvo autorización aeronáutica especial.
- **Prohibición estricta de acciones cinéticas o interferencia electromagnética:** El agente IA y el tablero SOC **NUNCA** deben recomendar inhibición de radiofrecuencia (*jamming*), secuestro de señal (*spoofing*), láser, redes o derribo de aeronaves. Toda recomendación defensiva se limita a verificación visual, monitoreo continuo, escalamiento al responsable de seguridad física, preservación de evidencia y aviso a autoridades competentes (Aerocivil / Fuerza Pública).

## 2. Niveles de Escalación y Revisión Humana
- **MONITOREAR (NORMAL / LOW):** Contacto dentro del umbral de altitud y a distancia segura del perímetro; mantener seguimiento en consola sin disparar alerta crítica.
- **VERIFICAR DETECCIÓN (REVIEW / MEDIUM):** Contacto que supera cota o se aproxima al perímetro, pero con confianza visual baja (< 0.50), ausente o discrepancia multi-sensor; exigir verificación visual humana antes de escalar.
- **NOTIFICAR Y VERIFICAR (CRITICAL / HIGH):** Contacto sobre umbral de altitud y/o dentro de zona de exclusión (< 150 m) con evidencia consistente; avisar de inmediato al responsable de seguridad conservando la revisión humana obligatoria.
- **SOLICITAR DATOS (INDETERMINATE):** Telemetría incompleta, negativa, nula o fuera de envolvente física.
