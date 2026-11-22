"""
AeroGuard - Construye el flujo de Orange (orange/AeroGuard_CRISP_DM.ows).

Flujo:
  File (entrenamiento) -> Data Table, Feature Statistics, Box Plot, Rank
  File (entrenamiento) -> Tree, Random Forest, Logistic Regression
  File (entrenamiento) + File (prueba lote 2) + modelos -> Test and Score
      (modo "Test on test data": entrena con el dataset principal y evalua
       con el lote adicional, que el modelo nunca vio)
  Test and Score -> Confusion Matrix ;  Tree -> Tree Viewer

Requisitos: orange3 y PyQt5. Ejecutar antes 03_export_orange.py.
Uso:  python data_mining/04_build_orange_workflow.py
"""

import argparse
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from AnyQt.QtWidgets import QApplication  # noqa: E402
from orangecanvas.registry import WidgetRegistry  # noqa: E402
from orangecanvas.scheme import Scheme, SchemeNode, SchemeLink  # noqa: E402
from orangecanvas.scheme.readwrite import scheme_to_ows_stream, scheme_load  # noqa: E402
from orangewidget.utils.filedialogs import RecentPath  # noqa: E402
from orangewidget.workflow.discovery import WidgetDiscovery  # noqa: E402
import Orange.canvas.config as orange_config  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORANGE_DIR = os.path.join(BASE_DIR, "orange")
WORKFLOW = os.path.join(ORANGE_DIR, "AeroGuard_CRISP_DM.ows")
TRAIN = "aeroguard_entrenamiento.csv.gz"
TEST = "aeroguard_prueba_lote2.csv.gz"
REGRESSION_DATA = "aeroguard_regresion_riesgo.csv.gz"

TEST_ON_TEST_DATA = 5  # indice de "Test on test data" en Test and Score
CROSS_VALIDATION = 0   # indice de CV (5 folds) en Test and Score para regresion


def build_registry():
    registry = WidgetRegistry()
    WidgetDiscovery(registry).run(orange_config.Config().widgets_entry_points())
    return registry


def file_settings(filename):
    path = os.path.join(ORANGE_DIR, filename)
    recent = RecentPath(abspath=path.replace("\\", "/"), prefix="basedir", relpath=filename, title=filename)
    return {"recent_paths": [recent], "source": 0, "controlAreaVisible": True}


def main():
    parser = argparse.ArgumentParser(description="Construye el flujo CRISP-DM de AeroGuard en Orange.")
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Agrega ramas de K-Means + Scatter Plot y Regresion Lineal (requiere aeroguard_regresion_riesgo.csv.gz).",
    )
    args = parser.parse_args()

    required = (TRAIN, TEST, REGRESSION_DATA) if args.extended else (TRAIN, TEST)
    for name in required:
        if not os.path.exists(os.path.join(ORANGE_DIR, name)):
            sys.exit(f"Falta orange/{name}. Ejecuta antes data_mining/03_export_orange.py.")

    app = QApplication.instance() or QApplication([])  # noqa: F841
    registry = build_registry()
    scheme = Scheme(
        title="AeroGuard - CRISP-DM en Orange",
        description="Entrena con el dataset principal y evalua con el lote adicional independiente.",
    )

    def node(qualified, title, x, y, properties=None):
        item = SchemeNode(registry.widget(qualified), title=title, position=(x, y))
        if properties:
            item.properties = properties
        scheme.add_node(item)
        return item

    def link(source, source_channel, sink, sink_channel):
        scheme.add_link(SchemeLink(source, source.output_channel(source_channel),
                                   sink, sink.input_channel(sink_channel)))

    train = node("Orange.widgets.data.owfile.OWFile", "Entrenamiento (dataset principal)", 80, 200,
                 file_settings(TRAIN))
    test = node("Orange.widgets.data.owfile.OWFile", "Prueba independiente (lote 2)", 80, 420,
                file_settings(TEST))
    table = node("Orange.widgets.data.owtable.OWTable", "Tabla de datos", 300, 40)
    stats = node("Orange.widgets.data.owfeaturestatistics.OWFeatureStatistics", "Estadísticas", 300, 120)
    boxplot = node("Orange.widgets.visualize.owboxplot.OWBoxPlot", "Box Plot", 300, 200)
    rank = node("Orange.widgets.data.owrank.OWRank", "Ranking de variables", 300, 280)
    tree = node("Orange.widgets.model.owtree.OWTreeLearner", "Árbol de decisión", 520, 140,
                {"max_depth": 12, "limit_depth": True, "min_internal": 10, "limit_min_internal": True,
                 "min_leaf": 5, "limit_min_leaf": True})
    forest = node("Orange.widgets.model.owrandomforest.OWRandomForest", "Random Forest", 520, 260,
                  {"n_estimators": 100, "max_depth": 16, "use_max_depth": True,
                   "min_samples_split": 5, "use_min_samples_split": True, "use_random_state": True})
    logreg = node("Orange.widgets.model.owlogisticregression.OWLogisticRegression",
                  "Regresión logística", 520, 380)
    score = node("Orange.widgets.evaluate.owtestandscore.OWTestAndScore", "Test and Score", 760, 300,
                 {"resampling": TEST_ON_TEST_DATA})
    confusion = node("Orange.widgets.evaluate.owconfusionmatrix.OWConfusionMatrix", "Matriz de confusión",
                     960, 300)
    viewer = node("Orange.widgets.visualize.owtreeviewer.OWTreeGraph", "Visor del árbol", 760, 140)

    for sink in (table, stats, boxplot, rank, tree, forest, logreg):
        link(train, "Data", sink, "Data")
    link(train, "Data", score, "Data")
    link(test, "Data", score, "Test Data")
    for learner in (tree, forest, logreg):
        link(learner, "Learner", score, "Learner")
    link(score, "Evaluation Results", confusion, "Evaluation Results")
    link(tree, "Model", viewer, "Tree")

    if args.extended:
        kmeans = node("Orange.widgets.unsupervised.owkmeans.OWKMeans", "K-Means (k=4)", 520, 500, {"k": 4})
        scatter = node("Orange.widgets.visualize.owscatterplot.OWScatterPlot", "Scatter Plot (Perfiles)", 760, 500)
        link(train, "Data", kmeans, "Data")
        link(kmeans, "Annotated Data", scatter, "Data")

        reg_file = node("Orange.widgets.data.owfile.OWFile", "Regresión riesgo (dataset)", 80, 620,
                        file_settings(REGRESSION_DATA))
        linreg = node("Orange.widgets.model.owlinearregression.OWLinearRegression", "Regresión lineal", 520, 620)
        score_reg = node("Orange.widgets.evaluate.owtestandscore.OWTestAndScore", "Test and Score (Regresión)",
                         760, 620, {"resampling": CROSS_VALIDATION})
        link(reg_file, "Data", linreg, "Data")
        link(reg_file, "Data", score_reg, "Data")
        link(linreg, "Learner", score_reg, "Learner")

    os.makedirs(ORANGE_DIR, exist_ok=True)
    with open(WORKFLOW, "wb") as fh:
        scheme_to_ows_stream(scheme, fh, pretty=True, pickle_fallback=True)

    # Verificacion: el archivo se vuelve a cargar con el registro de Orange.
    check = Scheme()
    with open(WORKFLOW, "rb") as fh:
        scheme_load(check, fh, registry=registry)
    print(f"Flujo guardado y verificado: {WORKFLOW} "
          f"({len(check.nodes)} widgets, {len(check.links)} conexiones)")


if __name__ == "__main__":
    main()
