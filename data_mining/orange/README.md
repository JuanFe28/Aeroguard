# AeroGuard en Orange Data Mining

Flujo CRISP-DM listo para abrir en [Orange](https://orangedatamining.com/) 3.x. Entrena con el dataset principal y **evalúa con un lote independiente** que el modelo nunca vio.

## Contenido

| Archivo | Qué es |
| --- | --- |
| `AeroGuard_CRISP_DM.ows` | Flujo de Orange (12 widgets). Ábrelo con *File → Open*. |
| `aeroguard_entrenamiento.csv.gz` | Dataset principal limpio: 125.000 → **108.750** registros. |
| `aeroguard_prueba_lote2.csv.gz` | Lote adicional limpio: 120.000 → **104.400** registros. |
| `resumen_limpieza.json` | Cuántos duplicados, celdas corruptas, filas fuera de rango y nulos se trataron en cada lote. |
| `resultados_orange.json` | Métricas de referencia calculadas con el motor de Orange. |

Los dos `.csv.gz` ya vienen con el encabezado de Orange: `threat_level` es la **clase** (variable objetivo), las 13 variables del modelo son atributos y los identificadores y coordenadas son metadatos. Orange abre los `.gz` directamente, sin descomprimirlos.

## Cómo usarlo

1. Abre Orange → *File → Open* → `data_mining/orange/AeroGuard_CRISP_DM.ows`.
2. Los dos widgets **File** cargan solos los `.csv.gz` de esta carpeta. Si Orange no los encuentra (por ejemplo, porque moviste el `.ows`), haz doble clic en cada File y elige el archivo.
3. Abre **Test and Score**: ya está en modo *Test on test data*, así que entrena con el principal y evalúa con el lote 2.
4. Abre **Matriz de confusión** y **Visor del árbol** para la sustentación.

```
Entrenamiento ─┬─> Tabla de datos / Estadísticas / Box Plot / Ranking   (Fase 2: comprensión)
               ├─> Árbol · Random Forest · Regresión logística          (Fase 4: modelado)
               └─> Test and Score <── Prueba independiente (lote 2)       (Fase 5: evaluación)
                        └─> Matriz de confusión     Árbol ─> Visor del árbol
```

## Resultados de referencia (prueba independiente, lote 2)

| Modelo | CA (accuracy) | F1 | Precisión | Recall | AUC |
| --- | --- | --- | --- | --- | --- |
| Random Forest | **95,4 %** | 0,954 | 0,955 | 0,954 | 0,979 |
| Árbol de decisión | 94,8 % | 0,948 | 0,948 | 0,948 | 0,952 |
| Regresión logística | 58,3 % | 0,561 | 0,591 | 0,583 | 0,655 |

Pueden variar unas décimas por el azar del Random Forest. La regresión logística queda muy por debajo porque el nivel de amenaza depende de **umbrales** (distancia, velocidad, altitud) que un modelo lineal no captura; sirve como línea base para justificar los árboles.

## Advertencia para la sustentación

Ambos lotes son **sintéticos**: `threat_level` lo asigna el generador con un puntaje por reglas. Un 95 % indica que el modelo recupera esas reglas, no que detecte amenazas reales. La validación con datos reales sigue pendiente (ver `docs/MINERIA_DATOS_CRISP_DM.md`).

## Regenerar los archivos

Desde la raíz del repositorio, con Python 3.11:

```powershell
py -3.11 -m venv .venv-dm
.venv-dm/Scripts/python.exe -m pip install -r data_mining/requirements.txt
.venv-dm/Scripts/python.exe data_mining/01_generate_dataset.py       # dataset principal (semilla 42)
.venv-dm/Scripts/python.exe data_mining/02_crisp_dm_pipeline.py      # pipeline scikit-learn + reglas
.venv-dm/Scripts/python.exe data_mining/03_export_orange.py          # limpia ambos lotes para Orange
.venv-dm/Scripts/python.exe data_mining/04_build_orange_workflow.py  # reconstruye el .ows
```

El lote 2 (`data/aeroguard_lote_adicional_120000.csv`) se conserva en el repositorio porque no lo produce ningún script con semilla fija.
