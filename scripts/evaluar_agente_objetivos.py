"""Evaluación reproducible con casos SINTÉTICOS, no datos de vuelo reales.

Ejecutar desde la raíz: python scripts/evaluar_agente_objetivos.py
"""
import csv
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.services.goal_based_agent import evaluate_goals  # noqa: E402


def reactive(drone, zone):
    """Referencia simple: alerta si altitud > umbral, sin validar confianza."""
    try:
        return 'NOTIFICAR_Y_VERIFICAR' if float(drone['altitude_m']) > float(zone['max_allowed_altitude_m']) else 'MONITOREAR'
    except (KeyError, TypeError, ValueError):
        return 'MONITOREAR'


def cases():
    rows = []
    for i in range(150):
        altitude = 70 + (i * 13) % 110
        confidence = round((i % 10) / 10, 2)
        drone = {'altitude_m': altitude, 'ai_confidence': confidence, 'speed_ms': i % 23}
        zone = {'max_allowed_altitude_m': 120}
        expected = ('VERIFICAR_DETECCION' if altitude > 120 and confidence < .5
                    else 'NOTIFICAR_Y_VERIFICAR' if altitude > 120 else 'MONITOREAR')
        rows.append((drone, zone, expected))
    # casos incompletos/incorrectos claramente etiquetados
    for invalid in ({}, {'altitude_m': 'nan'}, {'altitude_m': -1}):
        rows.append((invalid, {'max_allowed_altitude_m': 120}, 'SOLICITAR_DATOS'))
    return rows


def main():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit('Instalar matplotlib para crear las tres gráficas') from exc

    out = ROOT / 'docs' / 'agente_objetivos' / 'resultados'
    out.mkdir(parents=True, exist_ok=True)
    sample = cases()
    predictions = {'Reactivo simple': [], 'Basado en objetivos': []}
    truth = [r[2] for r in sample]
    for drone, zone, _ in sample:
        predictions['Reactivo simple'].append(reactive(drone, zone))
        predictions['Basado en objetivos'].append(evaluate_goals(drone, zone).action)
    scores = {name: round(100 * sum(a == b for a, b in zip(values, truth)) / len(truth), 2)
              for name, values in predictions.items()}
    with (out / 'casos_sinteticos.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['caso', 'altitud_m', 'confianza', 'accion_esperada', 'reactivo', 'objetivos'])
        for i, ((drone, _, expected), r, g) in enumerate(zip(sample, *predictions.values()), 1):
            writer.writerow([i, drone.get('altitude_m'), drone.get('ai_confidence'), expected, r, g])

    plt.figure(figsize=(7, 4))
    plt.bar(list(scores), list(scores.values()))
    plt.ylabel('Coincidencia con regla esperada (%)')
    plt.ylim(0, 105)
    plt.title('1. Efectividad en escenarios sintéticos')
    plt.tight_layout()
    plt.savefig(out / '01_efectividad.png', dpi=150)
    plt.close()

    sizes = [10, 50, 100, 500]
    times = {}
    for name, fn in [('Reactivo simple', lambda d,z: reactive(d,z)),
                     ('Basado en objetivos', lambda d,z: evaluate_goals(d,z).action)]:
        measured = []
        for size in sizes:
            vals = []
            for _ in range(10):
                begin = time.perf_counter_ns()
                for i in range(size):
                    d, z, _ = sample[i % len(sample)]
                    fn(d, z)
                vals.append((time.perf_counter_ns() - begin) / 1e6)
            measured.append(round(statistics.median(vals), 4))
        times[name] = measured
    plt.figure(figsize=(7, 4))
    for name, values in times.items():
        plt.plot(sizes, values, marker='o', label=name)
    plt.xlabel('Número de evaluaciones secuenciales')
    plt.ylabel('Mediana de tiempo (ms), 10 repeticiones')
    plt.title('2. Tiempo de decisión local sin red ni BD')
    plt.legend()
    plt.tight_layout()
    plt.savefig(out / '02_tiempos.png', dpi=150)
    plt.close()

    categories = ['MONITOREAR', 'VERIFICAR_DETECCION', 'NOTIFICAR_Y_VERIFICAR', 'SOLICITAR_DATOS']
    plt.figure(figsize=(9, 4))
    x = list(range(len(categories)))
    for shift, (name, values) in zip([-.18,.18], predictions.items()):
        plt.bar([v+shift for v in x], [values.count(category) for category in categories], width=.35, label=name)
    plt.xticks(x, ['Monitorear', 'Verificar', 'Notificar', 'Pedir datos'])
    plt.ylabel('Número de decisiones')
    plt.title('3. Distribución de decisiones ante mismos casos sintéticos')
    plt.legend()
    plt.tight_layout()
    plt.savefig(out / '03_decisiones.png', dpi=150)
    plt.close()

    payload = {'tipo_datos': 'sinteticos', 'casos': len(sample), 'efectividad_por_reglas_pct': scores,
               'tiempos_medianas_ms': dict(zip(times.keys(), (dict(zip(sizes, vals)) for vals in times.values()))),
               'advertencia': 'No es precisión de visión artificial ni latencia extremo a extremo.'}
    (out / 'metricas.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'ANALISIS.md').write_text(
        f'''# Análisis de las tres gráficas — AeroGuard\n\n'''
        f'''**Alcance:** {len(sample)} casos artificiales evaluados con reglas conocidas. No es una prueba de detección de drones reales.\n\n'''
        f'''1. **Efectividad:** el reactivo simple acertó {scores['Reactivo simple']} % y el basado en objetivos {scores['Basado en objetivos']} % frente a las reglas de referencia definidas para este experimento. La mejora representa manejo de confianza baja y datos inválidos, no capacidad de reconocimiento visual.\n'''
        f'''2. **Eficiencia:** se midió la mediana de 10 ejecuciones secuenciales para 10, 50, 100 y 500 decisiones. El modelo basado en objetivos puede consumir más tiempo por las verificaciones y trazabilidad, pero estos tiempos excluyen API, red, persistencia y sensores. Resultados exactos en `metricas.json`.\n'''
        f'''3. **Distribución:** el reactivo solo monitorea/notifica; el basado en objetivos permite solicitar datos y revisión de baja confianza, evitando tratar todos los casos como evidencia concluyente.\n\n'''
        f'''**Limitaciones:** referencias definidas con las mismas reglas de negocio; no evalúan generalización, falsos positivos frente a etiquetas independientes ni sistemas físicos.\n''',
        encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
