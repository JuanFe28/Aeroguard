"""
AeroGuard - Construye flujos reproducibles de Orange Data Mining (.ows):
  - Por defecto: orange/AeroGuard_CRISP_DM.ows (12 widgets de clasificacion y EDA)
  - Con --extended: orange/AeroGuard_CRISP_DM_6Modelos.ows (17 widgets: agrega K-Means k=4
    -> Scatter Plot y Regresion Lineal sobre aeroguard_regresion_riesgo.csv.gz)

Funciona tanto de forma nativa con Orange3 + PyQt5 como mediante generacion XML
directa compatible con el esquema Orange 3.41 (<scheme version="2.0">) cuando no hay
entorno Qt/Orange3 en la maquina de compilacion.

Uso:
  python data_mining/04_build_orange_workflow.py
  python data_mining/04_build_orange_workflow.py --extended --output data_mining/orange/AeroGuard_CRISP_DM_6Modelos.ows
"""

import argparse
import base64
import os
import pickle
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORANGE_DIR = os.path.join(BASE_DIR, "orange")
DEFAULT_WORKFLOW = os.path.join(ORANGE_DIR, "AeroGuard_CRISP_DM.ows")
EXTENDED_WORKFLOW = os.path.join(ORANGE_DIR, "AeroGuard_CRISP_DM_6Modelos.ows")
TRAIN = "aeroguard_entrenamiento.csv.gz"
TEST = "aeroguard_prueba_lote2.csv.gz"
REGRESSION_DATA = "aeroguard_regresion_riesgo.csv.gz"

TEST_ON_TEST_DATA = 5  # indice de "Test on test data" en Test and Score
CROSS_VALIDATION = 0   # indice de CV (5 folds) en Test and Score para regresion


def _make_recent_path_pickle_b64(filename: str) -> str:
    """Construye el pickle RecentPath compatible con orangewidget.utils.filedialogs."""
    # Construimos un payload compatible sin requerir que orangewidget este importable:
    # replicamos el formato exacto de protocol=4 observado en AeroGuard_CRISP_DM.ows.
    path = os.path.join(ORANGE_DIR, filename).replace("\\", "/")

    # Intentar importar RecentPath real si Orange esta instalado
    try:
        from orangewidget.utils.filedialogs import RecentPath  # noqa: E402

        recent = RecentPath(abspath=path, prefix="basedir", relpath=filename, title=filename)
        payload = {"recent_paths": [recent], "source": 0, "controlAreaVisible": True}
        return base64.encodebytes(pickle.dumps(payload, protocol=4)).decode("ascii").strip()
    except ImportError:
        pass

    # Fallback puro usando los mismos opcodes de protocol=4 para orangewidget.utils.filedialogs.RecentPath
    # Usamos pickletools/protocolo 4 manual ensamblando objeto stub bajo el mismo module/qualname
    class _RecentPathProxy:
        def __reduce__(self):
            return (_RecentPathReconstructor, (), self.__dict__)

    class _RecentPathReconstructor:
        pass

    # Mas limpio y exacto: reemplazar la clase temporal via pickle module lookup override
    import types

    mod = types.ModuleType("orangewidget.utils.filedialogs")

    class RecentPath:
        __module__ = "orangewidget.utils.filedialogs"
        __qualname__ = "RecentPath"

        def __init__(self, abspath, prefix, relpath, title, sheet="", file_format=None):
            self.abspath = abspath
            self.prefix = prefix
            self.relpath = relpath
            self.title = title
            self.sheet = sheet
            self.file_format = file_format

    mod.RecentPath = RecentPath
    orig_mod = sys.modules.get("orangewidget.utils.filedialogs")
    orig_parent = sys.modules.get("orangewidget")
    orig_utils = sys.modules.get("orangewidget.utils")
    try:
        sys.modules.setdefault("orangewidget", types.ModuleType("orangewidget"))
        sys.modules.setdefault("orangewidget.utils", types.ModuleType("orangewidget.utils"))
        sys.modules["orangewidget.utils.filedialogs"] = mod
        recent = RecentPath(abspath=path, prefix="basedir", relpath=filename, title=filename)
        payload = {"recent_paths": [recent], "source": 0, "controlAreaVisible": True}
        raw = pickle.dumps(payload, protocol=4)
        return base64.encodebytes(raw).decode("ascii").strip()
    finally:
        if orig_mod is not None:
            sys.modules["orangewidget.utils.filedialogs"] = orig_mod
        else:
            sys.modules.pop("orangewidget.utils.filedialogs", None)
        if orig_utils is None:
            sys.modules.pop("orangewidget.utils", None)
        if orig_parent is None:
            sys.modules.pop("orangewidget", None)


def build_xml_scheme(extended: bool, workflow_path: str) -> None:
    """Genera el esquema XML <scheme version='2.0'> sin requerir GUI Qt/PyQt5."""
    nodes = [
        ("0", "File", "Orange.widgets.data.owfile.OWFile", "Orange3", "Entrenamiento (dataset principal)", "(80, 200)"),
        ("1", "File", "Orange.widgets.data.owfile.OWFile", "Orange3", "Prueba independiente (lote 2)", "(80, 420)"),
        ("2", "Data Table", "Orange.widgets.data.owtable.OWTable", "Orange3", "Tabla de datos", "(300, 40)"),
        ("3", "Column Statistics", "Orange.widgets.data.owfeaturestatistics.OWFeatureStatistics", "Orange3", "Estadísticas", "(300, 120)"),
        ("4", "Box Plot", "Orange.widgets.visualize.owboxplot.OWBoxPlot", "Orange3", "Box Plot", "(300, 200)"),
        ("5", "Rank", "Orange.widgets.data.owrank.OWRank", "Orange3", "Ranking de variables", "(300, 280)"),
        ("6", "Tree", "Orange.widgets.model.owtree.OWTreeLearner", "Orange3", "Árbol de decisión", "(520, 140)"),
        ("7", "Random Forest", "Orange.widgets.model.owrandomforest.OWRandomForest", "Orange3", "Random Forest", "(520, 260)"),
        ("8", "Logistic Regression", "Orange.widgets.model.owlogisticregression.OWLogisticRegression", "Orange3", "Regresión logística", "(520, 380)"),
        ("9", "Test and Score", "Orange.widgets.evaluate.owtestandscore.OWTestAndScore", "Orange3", "Test and Score", "(760, 300)"),
        ("10", "Confusion Matrix", "Orange.widgets.evaluate.owconfusionmatrix.OWConfusionMatrix", "Orange3", "Matriz de confusión", "(960, 300)"),
        ("11", "Tree Viewer", "Orange.widgets.visualize.owtreeviewer.OWTreeGraph", "Orange3", "Visor del árbol", "(760, 140)"),
    ]
    links = [
        ("0", "0", "2", "Data", "Data", "data", "data"),
        ("1", "0", "3", "Data", "Data", "data", "data"),
        ("2", "0", "4", "Data", "Data", "data", "data"),
        ("3", "0", "5", "Data", "Data", "data", "data"),
        ("4", "0", "6", "Data", "Data", "data", "data"),
        ("7", "0", "9", "Data", "Data", "data", "train_data"),
        ("8", "1", "9", "Data", "Test Data", "data", "test_data"),
        ("9", "6", "9", "Learner", "Learner", "learner", "learner"),
        ("10", "7", "9", "Learner", "Learner", "learner", "learner"),
        ("11", "8", "9", "Learner", "Learner", "learner", "learner"),
        ("12", "9", "10", "Evaluation Results", "Evaluation Results", "evaluations_results", "evaluation_results"),
        ("13", "6", "11", "Model", "Tree", "model", "tree"),
    ]
    if not extended:
        links.insert(5, ("5", "0", "7", "Data", "Data", "data", "data"))
        links.insert(6, ("6", "0", "8", "Data", "Data", "data", "data"))
    props = [
        ("0", "pickle", _make_recent_path_pickle_b64(TRAIN)),
        ("1", "pickle", _make_recent_path_pickle_b64(TEST)),
        ("6", "literal", "{'max_depth': 12, 'limit_depth': True, 'min_internal': 10, 'limit_min_internal': True, 'min_leaf': 5, 'limit_min_leaf': True}"),
        ("7", "literal", "{'n_estimators': 100, 'max_depth': 16, 'use_max_depth': True, 'min_samples_split': 5, 'use_min_samples_split': True, 'use_random_state': True}"),
        ("9", "literal", "{'__version__': 4, 'resampling': 5}"),
    ]

    if extended:
        nodes.extend(
            [
                ("12", "k-Means", "Orange.widgets.unsupervised.owkmeans.OWKMeans", "Orange3", "K-Means (k=4)", "(520, 500)"),
                ("13", "Scatter Plot", "Orange.widgets.visualize.owscatterplot.OWScatterPlot", "Orange3", "Scatter Plot (Perfiles)", "(760, 500)"),
                ("14", "File", "Orange.widgets.data.owfile.OWFile", "Orange3", "Regresión riesgo (dataset)", "(80, 620)"),
                ("15", "Linear Regression", "Orange.widgets.model.owlinearregression.OWLinearRegression", "Orange3", "Regresión lineal", "(520, 620)"),
                ("16", "Test and Score", "Orange.widgets.evaluate.owtestandscore.OWTestAndScore", "Orange3", "Test and Score (Regresión)", "(760, 620)"),
                ("17", "Preprocess", "Orange.widgets.data.owpreprocess.OWPreprocess", "Orange3", "Normalizar (LogReg)", "(300, 380)"),
            ]
        )
        links.extend(
            [
                ("14", "0", "12", "Data", "Data", "data", "data"),
                ("15", "12", "13", "Data", "Data", "annotated_data", "data"),
                ("16", "14", "16", "Data", "Data", "data", "train_data"),
                ("17", "15", "16", "Learner", "Learner", "learner", "learner"),
                ("18", "17", "8", "Preprocessor", "Preprocessor", "preprocessor", "preprocessor"),
            ]
        )
        props.extend(
            [
                ("12", "literal", "{'k': 4}"),
                ("14", "pickle", _make_recent_path_pickle_b64(REGRESSION_DATA)),
                ("16", "literal", "{'__version__': 4, 'resampling': 0, 'n_folds': 2}"),
                (
                    "17",
                    "literal",
                    "{'__version__': 2, 'storedsettings': {'preprocessors': [('orange.preprocess.continuize', {}), ('orange.preprocess.impute', {}), ('orange.preprocess.scale', {})]}}",
                ),
            ]
        )

    title = (
        "AeroGuard - CRISP-DM Completo (Clasificacion + K-Means + Regresion Lineal)"
        if extended
        else "AeroGuard - CRISP-DM en Orange"
    )
    desc = (
        "Incluye clasificacion (Tree/RF/LogReg sobre Lote 2), clustering K-Means (k=4 -> Scatter Plot) y Regresion Lineal (risk_score)."
        if extended
        else "Entrena con el dataset principal y evalua con el lote adicional independiente."
    )

    lines = [
        "<?xml version='1.0' encoding='utf-8'?>",
        f'<scheme version="2.0" title="{escape(title)}" description="{escape(desc)}">',
        "\t<nodes>",
    ]
    for nid, name, qname, proj, wtitle, pos in nodes:
        lines.append(
            f'\t\t<node id="{nid}" name="{escape(name)}" qualified_name="{escape(qname)}" '
            f'project_name="{escape(proj)}" version="" title="{escape(wtitle)}" position="{pos}" />'
        )
    lines.append("\t</nodes>")
    lines.append("\t<links>")
    for lid, src, dst, sc, dc, scid, dcid in links:
        lines.append(
            f'\t\t<link id="{lid}" source_node_id="{src}" sink_node_id="{dst}" '
            f'source_channel="{escape(sc)}" sink_channel="{escape(dc)}" enabled="true" '
            f'source_channel_id="{escape(scid)}" sink_channel_id="{escape(dcid)}" />'
        )
    lines.extend(["\t</links>", "\t<annotations />", "\t<thumbnail />", "\t<node_properties>"])
    for nid, fmt, body in props:
        lines.append(f'\t\t<properties node_id="{nid}" format="{fmt}">{body}</properties>')
    lines.extend(["\t</node_properties>", "\t<session_state>", "\t\t<window_groups />", "\t</session_state>", "</scheme>"])

    os.makedirs(ORANGE_DIR, exist_ok=True)
    with open(workflow_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    # Validar XML bien formado
    parsed = ET.parse(workflow_path).getroot()
    n_count = len(parsed.findall("./nodes/node"))
    l_count = len(parsed.findall("./links/link"))
    print(f"Flujo XML guardado y validado: {workflow_path} ({n_count} widgets, {l_count} conexiones)")


def main():
    parser = argparse.ArgumentParser(description="Construye el flujo CRISP-DM de AeroGuard en Orange.")
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Genera el flujo extendido con K-Means + Scatter Plot y Regresion Lineal (requiere aeroguard_regresion_riesgo.csv.gz).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Ruta de salida personalizada para el archivo .ows.",
    )
    args = parser.parse_args()

    workflow_path = args.output or (EXTENDED_WORKFLOW if args.extended else DEFAULT_WORKFLOW)
    required = (TRAIN, TEST, REGRESSION_DATA) if args.extended else (TRAIN, TEST)
    for name in required:
        if not os.path.exists(os.path.join(ORANGE_DIR, name)):
            sys.exit(f"Falta orange/{name}. Ejecuta antes data_mining/03_export_orange.py.")

    # Si Orange3 + PyQt5 estan disponibles, usar esquema nativo; sino generar esquema XML compatible
    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from AnyQt.QtWidgets import QApplication  # noqa: E402
        from orangecanvas.registry import WidgetRegistry  # noqa: E402
        from orangecanvas.scheme import Scheme, SchemeNode, SchemeLink  # noqa: E402
        from orangecanvas.scheme.readwrite import scheme_to_ows_stream, scheme_load  # noqa: E402
        from orangewidget.utils.filedialogs import RecentPath  # noqa: E402
        from orangewidget.workflow.discovery import WidgetDiscovery  # noqa: E402
        import Orange.canvas.config as orange_config  # noqa: E402
    except ImportError:
        build_xml_scheme(extended=args.extended, workflow_path=workflow_path)
        return

    app = QApplication.instance() or QApplication([])  # noqa: F841
    registry = WidgetRegistry()
    WidgetDiscovery(registry).run(orange_config.Config().widgets_entry_points())
    scheme = Scheme(
        title="AeroGuard - CRISP-DM Completo" if args.extended else "AeroGuard - CRISP-DM en Orange",
        description="Entrena con el dataset principal y evalua con el lote adicional independiente.",
    )

    def node(qualified, title, x, y, properties=None):
        item = SchemeNode(registry.widget(qualified), title=title, position=(x, y))
        if properties:
            item.properties = properties
        scheme.add_node(item)
        return item

    def link(source, source_channel, sink, sink_channel):
        scheme.add_link(SchemeLink(source, source.output_channel(source_channel), sink, sink.input_channel(sink_channel)))

    def file_settings(filename):
        path = os.path.join(ORANGE_DIR, filename)
        recent = RecentPath(abspath=path.replace("\\", "/"), prefix="basedir", relpath=filename, title=filename)
        return {"recent_paths": [recent], "source": 0, "controlAreaVisible": True}

    train = node("Orange.widgets.data.owfile.OWFile", "Entrenamiento (dataset principal)", 80, 200, file_settings(TRAIN))
    test = node("Orange.widgets.data.owfile.OWFile", "Prueba independiente (lote 2)", 80, 420, file_settings(TEST))
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
    logreg = node("Orange.widgets.model.owlogisticregression.OWLogisticRegression", "Regresión logística", 520, 380)
    score = node("Orange.widgets.evaluate.owtestandscore.OWTestAndScore", "Test and Score", 760, 300,
                 {"__version__": 4, "resampling": TEST_ON_TEST_DATA})
    confusion = node("Orange.widgets.evaluate.owconfusionmatrix.OWConfusionMatrix", "Matriz de confusión", 960, 300)
    viewer = node("Orange.widgets.visualize.owtreeviewer.OWTreeGraph", "Visor del árbol", 760, 140)

    data_sinks = (table, stats, boxplot, rank, tree) if args.extended else (table, stats, boxplot, rank, tree, forest, logreg)
    for sink in data_sinks:
        link(train, "Data", sink, "Data")
    link(train, "Data", score, "Data")
    link(test, "Data", score, "Test Data")
    for learner in (tree, forest, logreg):
        link(learner, "Learner", score, "Learner")
    link(score, "Evaluation Results", confusion, "Evaluation Results")
    link(tree, "Model", viewer, "Tree")

    if args.extended:
        preprocess = node(
            "Orange.widgets.data.owpreprocess.OWPreprocess",
            "Normalizar (LogReg)",
            300,
            380,
            {
                "__version__": 2,
                "storedsettings": {
                    "preprocessors": [
                        ("orange.preprocess.continuize", {}),
                        ("orange.preprocess.impute", {}),
                        ("orange.preprocess.scale", {}),
                    ]
                },
            },
        )
        link(preprocess, "Preprocessor", logreg, "Preprocessor")

        kmeans = node("Orange.widgets.unsupervised.owkmeans.OWKMeans", "K-Means (k=4)", 520, 500, {"k": 4})
        scatter = node("Orange.widgets.visualize.owscatterplot.OWScatterPlot", "Scatter Plot (Perfiles)", 760, 500)
        link(train, "Data", kmeans, "Data")
        link(kmeans, "Data", scatter, "Data")

        reg_file = node("Orange.widgets.data.owfile.OWFile", "Regresión riesgo (dataset)", 80, 620, file_settings(REGRESSION_DATA))
        linreg = node("Orange.widgets.model.owlinearregression.OWLinearRegression", "Regresión lineal", 520, 620)
        score_reg = node("Orange.widgets.evaluate.owtestandscore.OWTestAndScore", "Test and Score (Regresión)",
                         760, 620, {"__version__": 4, "resampling": CROSS_VALIDATION, "n_folds": 2})
        link(reg_file, "Data", score_reg, "Data")
        link(linreg, "Learner", score_reg, "Learner")

    os.makedirs(ORANGE_DIR, exist_ok=True)
    with open(workflow_path, "wb") as fh:
        scheme_to_ows_stream(scheme, fh, pretty=True, pickle_fallback=True)

    check = Scheme()
    with open(workflow_path, "rb") as fh:
        scheme_load(check, fh, registry=registry)
    print(f"Flujo guardado y verificado: {workflow_path} ({len(check.nodes)} widgets, {len(check.links)} conexiones)")


if __name__ == "__main__":
    main()
