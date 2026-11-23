"""Generador del informe Word (.docx) de Mineria de Datos CRISP-DM y Orange 3.41.

Construye ``docs/AeroGuard_Mineria_Datos_Orange_CRISP_DM.docx`` combinando el
analisis predictivo de los 6 modelos CRISP-DM, el diccionario de datos, la
transformacion de datos (4 pilares), la matriz de madurez digital e IA (6x5),
las figuras analiticas de ARIMA/resumen y las 7 capturas verificadas de
Orange Data Mining 3.41.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable, Sequence

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DOCX = REPO_ROOT / "docs" / "AeroGuard_Mineria_Datos_Orange_CRISP_DM.docx"
CAPTURAS_DIR = REPO_ROOT / "data_mining" / "orange" / "capturas"
FIGURES_DIR = REPO_ROOT / "data_mining" / "reports" / "figures"

NAVY = RGBColor(0x0F, 0x29, 0x42)
CYAN = RGBColor(0x0E, 0x74, 0x90)
TEXT_DARK = RGBColor(0x1E, 0x29, 0x3B)
TEXT_MUTED = RGBColor(0x47, 0x55, 0x69)

HEX_NAVY = "0F2942"
HEX_ALT_ROW = "F8FAFC"
HEX_CALLOUT_BG = "EFF6FF"
HEX_CALLOUT_BORDER = "0E7490"
HEX_WARN_BG = "FEFCE8"
HEX_WARN_BORDER = "CA8A04"
HEX_BORDER = "CBD5E1"


def _set_cell_shading(cell, fill_hex: str) -> None:
    """Apply background shading to a Word table cell."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_cell_margins(cell, top: int = 80, bottom: int = 80, left: int = 110, right: int = 110) -> None:
    """Set compact padding (in dxa) on a Word table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = OxmlElement("w:tcMar")
    for side, value in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        tc_mar.append(node)
    tc_pr.append(tc_mar)


def _set_table_borders(table, border_hex: str = HEX_BORDER) -> None:
    """Configure thin clean borders around and inside a table."""
    tbl_pr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="{border_hex}"/>'
        f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="{HEX_NAVY}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{border_hex}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>'
        f"</w:tblBorders>"
    )
    tbl_pr.append(borders)


def _prevent_row_split(row) -> None:
    """Keep table rows intact across page boundaries."""
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:cantSplit"))


def _repeat_header_row(row) -> None:
    """Repeat the header row when a table spans multiple pages."""
    tr_pr = row._tr.get_or_add_trPr()
    tr_pr.append(OxmlElement("w:tblHeader"))


def _add_page_number_field(paragraph) -> None:
    """Append 'Pagina X de Y' dynamic fields to the footer paragraph."""
    for label, field in (("Página ", "PAGE"), (" de ", "NUMPAGES")):
        r_text = paragraph.add_run(label)
        r_text.font.name = "Calibri"
        r_text.font.size = Pt(8.5)
        r_text.font.color.rgb = TEXT_MUTED

        r_field = paragraph.add_run()
        r_field.font.name = "Calibri"
        r_field.font.size = Pt(8.5)
        r_field.font.color.rgb = TEXT_MUTED
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = f" {field} "
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        r_field._r.extend([begin, instr, end])


def _configure_document(doc: Document) -> None:
    """Configure margins, typography styles, header, and footer."""
    for section in doc.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
        section.different_first_page_header_footer = True

        hdr_p = section.header.paragraphs[0]
        hdr_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hdr_run = hdr_p.add_run(
            "AeroGuard C-UAS · Minería de Datos CRISP-DM y Orange Data Mining 3.41"
        )
        hdr_run.font.name = "Calibri"
        hdr_run.font.size = Pt(8.5)
        hdr_run.font.color.rgb = TEXT_MUTED

        ftr_p = section.footer.paragraphs[0]
        ftr_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_left = ftr_p.add_run("Unidades Tecnológicas de Santander (UTS) · Rama feat/juan   |   ")
        r_left.font.name = "Calibri"
        r_left.font.size = Pt(8.5)
        r_left.font.color.rgb = TEXT_MUTED
        _add_page_number_field(ftr_p)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = TEXT_DARK
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.15


def _add_h1(doc: Document, text: str) -> None:
    """Add a styled Section Heading 1 with bottom accent rule."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = NAVY
    p_pr = p._p.get_or_add_pPr()
    p_bdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'<w:bottom w:val="single" w:sz="8" w:space="4" w:color="{HEX_CALLOUT_BORDER}"/>'
        f"</w:pBdr>"
    )
    p_pr.append(p_bdr)


def _add_h2(doc: Document, text: str) -> None:
    """Add a styled Subsection Heading 2."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = "Calibri"
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = CYAN


def _add_body(doc: Document, text: str, bold_prefix: str = "") -> None:
    """Add a standard body paragraph with an optional bold lead-in."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(5)
    if bold_prefix:
        lead = p.add_run(bold_prefix)
        lead.font.bold = True
        lead.font.color.rgb = NAVY
    run = p.add_run(text)
    run.font.color.rgb = TEXT_DARK


def _add_bullets(doc: Document, items: Iterable[tuple[str, str]]) -> None:
    """Add clean bullet points with bold lead-in phrases."""
    for lead_text, body_text in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.12
        if lead_text:
            lead = p.add_run(lead_text)
            lead.font.bold = True
            lead.font.color.rgb = NAVY
        body = p.add_run(body_text)
        body.font.color.rgb = TEXT_DARK


def _add_callout(
    doc: Document,
    title: str,
    body: str,
    *,
    fill_hex: str = HEX_CALLOUT_BG,
    border_hex: str = HEX_CALLOUT_BORDER,
) -> None:
    """Render an accented single-cell callout panel for rigor notes or rules."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.9)
    _set_cell_shading(cell, fill_hex)
    _set_cell_margins(cell, top=110, bottom=110, left=160, right=140)
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_pr.append(
        parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_hex}"/>'
            f'<w:top w:val="none"/><w:right w:val="none"/><w:bottom w:val="none"/>'
            f"</w:tcBorders>"
        )
    )
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    t_run = p.add_run(f"{title} ")
    t_run.font.bold = True
    t_run.font.size = Pt(10)
    t_run.font.color.rgb = NAVY
    b_run = p.add_run(body)
    b_run.font.size = Pt(9.5)
    b_run.font.color.rgb = TEXT_DARK
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(3)


def _add_styled_table(
    doc: Document,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths_in: Sequence[float],
    *,
    font_size_pt: float = 8.5,
) -> None:
    """Create a bordered, zebra-striped table with fixed column widths."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _set_table_borders(table)

    hdr_row = table.rows[0]
    _repeat_header_row(hdr_row)
    _prevent_row_split(hdr_row)
    for idx, heading in enumerate(headers):
        cell = hdr_row.cells[idx]
        cell.width = Inches(col_widths_in[idx])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        _set_cell_shading(cell, HEX_NAVY)
        _set_cell_margins(cell, top=80, bottom=80, left=85, right=85)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(heading)
        run.font.name = "Calibri"
        run.font.size = Pt(font_size_pt)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for r_idx, row_vals in enumerate(rows):
        row = table.rows[r_idx + 1]
        _prevent_row_split(row)
        bg = HEX_ALT_ROW if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = Inches(col_widths_in[c_idx])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            _set_cell_shading(cell, bg)
            _set_cell_margins(cell, top=65, bottom=65, left=85, right=85)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.1
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(font_size_pt)
            if c_idx == 0:
                run.font.bold = True
                run.font.color.rgb = NAVY
            else:
                run.font.color.rgb = TEXT_DARK

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(4)


def _add_figure(
    doc: Document,
    image_path: Path,
    caption: str,
    *,
    width_in: float = 6.3,
    subtitle: str = "",
) -> None:
    """Embed a verified PNG screenshot or chart centered with its caption."""
    if not image_path.is_file():
        raise FileNotFoundError(f"No se encontró la imagen requerida: {image_path}")

    if subtitle:
        p_sub = doc.add_paragraph()
        p_sub.paragraph_format.space_before = Pt(6)
        p_sub.paragraph_format.space_after = Pt(3)
        p_sub.paragraph_format.keep_with_next = True
        r_sub = p_sub.add_run(subtitle)
        r_sub.font.bold = True
        r_sub.font.size = Pt(10)
        r_sub.font.color.rgb = NAVY

    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(2)
    p_img.paragraph_format.space_after = Pt(3)
    p_img.paragraph_format.keep_with_next = True
    p_img.add_run().add_picture(str(image_path), width=Inches(width_in))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(8)
    r_cap = p_cap.add_run(caption)
    r_cap.font.italic = True
    r_cap.font.size = Pt(9)
    r_cap.font.color.rgb = TEXT_MUTED


def _add_cover(doc: Document) -> None:
    """Build a compact structured cover page for academic/technical submission."""
    banner = doc.add_table(rows=1, cols=1)
    banner.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = banner.cell(0, 0)
    cell.width = Inches(6.9)
    _set_cell_shading(cell, HEX_NAVY)
    _set_cell_margins(cell, top=220, bottom=220, left=220, right=220)

    p1 = cell.paragraphs[0]
    p1.paragraph_format.space_after = Pt(4)
    r1 = p1.add_run("AEROGUARD C-UAS · PROYECTO DE ANALÍTICA E INTELIGENCIA ARTIFICIAL")
    r1.font.size = Pt(9.5)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0x67, 0xE8, 0xF9)

    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(6)
    r2 = p2.add_run("Minería de Datos Predictiva (CRISP-DM), Madurez IA y Manual Visual en Orange Data Mining 3.41")
    r2.font.size = Pt(18)
    r2.font.bold = True
    r2.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    p3 = cell.add_paragraph()
    p3.paragraph_format.space_after = Pt(0)
    r3 = p3.add_run(
        "Unidades Tecnológicas de Santander (UTS) · Versión 1.2.0-rc.2 (Rama feat/juan) · Evidencias Verificadas"
    )
    r3.font.size = Pt(10)
    r3.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(6)

    meta_rows = [
        ("Volumen auditado", "125,000 registros brutos -> 108,750 limpios (Lote 1) | 120,000 brutos -> 104,400 limpios (Lote 2 independiente)"),
        ("Metodología", "CRISP-DM en 6 fases + validación visual externa en Orange Data Mining 3.41.0 (18 widgets, 17 conexiones)"),
        ("Modelos evaluados", "Regresión Lineal, Regresión Logística, K-Means (k=4), Árbol de Decisión, Random Forest y ARIMA(1,1,1)"),
        ("Artefacto en producción", "backend/app/data/predictive_models_artifact.json (862.4 KB, paridad 100.00%, inferencia < 2 ms en Oracle ARM64)"),
        ("Flujo Orange ejecutable", "data_mining/orange/AeroGuard_CRISP_DM_6Modelos.ows (incluye Normalizar para LogReg, K-Means y Regresión Lineal)"),
        ("Fecha de compilación", f"{date(2026, 11, 22).isoformat()} · Documentación viva de repositorio (docs/MINERIA_DATOS_CRISP_DM.md)"),
    ]
    _add_styled_table(
        doc,
        headers=("Ficha Técnica", "Especificación Verificada en Repositorio"),
        rows=meta_rows,
        col_widths_in=(1.9, 5.0),
        font_size_pt=9.0,
    )

    _add_callout(
        doc,
        "Advertencia de Rigor Científico:",
        "Los datasets de este módulo son sintéticos (threat_level y risk_score derivan de reglas cinemáticas del generador). "
        "Las métricas obtenidas (Accuracy > 95 %, R² = 0.9356, ROC-AUC = 0.9689, MAPE = 6.77 %) comprueban consistencia matemática "
        "y recuperación de patrones en un entorno controlado; no constituyen evidencia de desempeño con drones o sensores físicos reales. "
        "Toda recomendación generada en la plataforma exige verificación humana.",
        fill_hex=HEX_WARN_BG,
        border_hex=HEX_WARN_BORDER,
    )

    _add_h2(doc, "Índice de Contenido")
    _add_bullets(
        doc,
        [
            ("1. Enfoque Predictivo y Fase 1 CRISP-DM: ", "Preguntas de negocio y selección del modelo productivo."),
            ("2. Comprensión e Identificación de Datos: ", "Diccionario de 21 atributos y distribución de calidad 80/10/10."),
            ("3. Preparación y Control de Data Leakage: ", "Limpieza unificada en clean_telemetry() y partición previa 80/20."),
            ("4. Comparativa de los 6 Modelos Predictivos: ", "Métricas Python vs Lote 2, perfiles K-Means, ARIMA, reglas e Oracle."),
            ("5. Transformación de Datos en Decisiones: ", "Cadena de 4 etapas y 4 pilares de gestión aplicados a AeroGuard."),
            ("6. Matriz de Madurez Digital e IA (6x5): ", "Diagnóstico sustentado TRL 4 y hoja de ruta al Nivel 4–5."),
            ("7. Orange Data Mining 3.41 y 7 Capturas Reales: ", "Sustentación, manual reproducible y capturas verificadas de pantalla."),
        ],
    )
    doc.add_page_break()


def build_report(output_path: Path = OUT_DOCX) -> Path:
    """Assemble and save the complete Word report with embedded Orange captures."""
    doc = Document()
    _configure_document(doc)
    _add_cover(doc)

    # ------------------------------------------------------------------
    # Seccion 1
    # ------------------------------------------------------------------
    _add_h1(doc, "1. Enfoque Predictivo y Fase 1: Comprensión del Negocio (CRISP-DM)")
    _add_body(
        doc,
        "A diferencia de la estadística puramente descriptiva (promedios o conteos históricos), AeroGuard implementa minería de datos "
        "predictiva para anticipar eventos, probabilidades de riesgo y tendencias operativas mediante cinco preguntas de negocio concretas:",
    )
    _add_bullets(
        doc,
        [
            ("1. Clasificación de amenaza (threat_level): ", "¿Cuál es el nivel táctico (LOW, MEDIUM, HIGH, CRITICAL) de un vector aéreo recién detectado según sus variables multisensor?"),
            ("2. Puntaje continuo de riesgo (risk_score, 0–100): ", "¿Cuál es la severidad cinemática continua para priorizar la cola de atención en el Centro de Operaciones (SOC)?"),
            ("3. Probabilidad de violación de geocerca: ", "¿Cuál es la probabilidad de que el contacto sea de alto riesgo y qué umbral de decisión minimiza falsas alarmas sin omitir incursiones?"),
            ("4. Segmentación de perfiles de vuelo: ", "¿Qué patrones operativos recurrentes emergen en el espacio aéreo sin depender de etiquetas previas?"),
            ("5. Pronóstico de demanda táctica (ARIMA): ", "¿Cuántos picos diarios de incursiones HIGH/CRITICAL se esperan en las próximas dos semanas para planificar cobertura de operadores?"),
        ],
    )

    # ------------------------------------------------------------------
    # Seccion 2
    # ------------------------------------------------------------------
    _add_h1(doc, "2. Fase 2: Comprensión e Identificación de los Datos")
    _add_body(
        doc,
        "El esquema analítico consolida 20 atributos base de telemetría multisensor más la variable continua derivada risk_score (21 campos). "
        "Los dos lotes suman 245,000 tramas brutas diseñadas con una inyección controlada de calidad: 80 % nominal, 10 % outliers físicos extremos "
        "(altitudes de 3,500–9,000 m, velocidades supersónicas 300–650 m/s, distancias > 150 km) y 10 % datos sucios (nulos, cadenas corruptas "
        "'SENSOR_ERR'/'???' y 3.0 % duplicados exactos).",
    )

    dict_rows = [
        ("1", "record_id", "String", "REC-000001...", "Identificador único de trama (metadato excluido de ML)."),
        ("2", "timestamp", "DateTime", "2026-01-01 .. 2026-10-31", "Estampa UTC; base de agregación diaria para ARIMA."),
        ("3", "drone_id", "String", "UAV-HK-xxx, UAV-COL-xxx", "Matrícula / firma reportada del vector aéreo (metadato)."),
        ("4", "sensor_id", "String", "5 sensores BGA/BOG", "Estación receptora (CAM-BGA-NORTE-01, RAD-BGA-SUR-02, etc.)."),
        ("5", "city_zone", "Categórico", "Bucaramanga, Bogota", "Jurisdicción geográfica protegida (feature categórica)."),
        ("6", "latitude", "Float", "~7.119 (BGA) / ~4.609 (BOG)", "Coordenada geodésica de latitud (metadato)."),
        ("7", "longitude", "Float", "~-73.122 (BGA) / ~-74.081 (BOG)", "Coordenada geodésica de longitud (metadato)."),
        ("8", "altitude_m", "Float", "10.0 a 280.0 m (nominal)", "Altura AGL observada; referencia normativa civil: 120 m."),
        ("9", "speed_ms", "Float", "0.5 a 32.0 m/s (nominal)", "Velocidad horizontal estimada del objetivo."),
        ("10", "vertical_speed_ms", "Float", "-8.0 a 12.0 m/s", "Tasa de ascenso o descenso vertical."),
        ("11", "heading_deg", "Float", "0.0° a 359.9°", "Rumbo magnético del desplazamiento."),
        ("12", "distance_to_zone_m", "Float", "20.0 a 1,950.0 m", "Distancia radial al centro de la zona restringida."),
        ("13", "rf_signal_dbm", "Float", "-105.0 a -35.0 dBm", "Potencia RSSI del enlace radioeléctrico de control (RF)."),
        ("14", "battery_est_pct", "Float", "8.0 % a 99.0 %", "Autonomía residual estimada de la aeronave."),
        ("15", "ai_confidence", "Float", "0.45 a 0.98", "Confianza visual declarada del detector."),
        ("16", "drone_class", "Categórico", "5 clases", "quadcopter, fixed_wing, hexacopter, diy_custom, bird_false_pos."),
        ("17", "weather_condition", "Categórico", "4 condiciones", "Despejado, Nublado, Lluvia, Niebla."),
        ("18", "wind_speed_kmh", "Float", "3.0 a 42.0 km/h", "Velocidad del viento en la zona de observación."),
        ("19", "flight_pattern", "Categórico", "5 patrones", "Directo, Erratico, Estacionario, Patrullaje, Evasivo."),
        ("20", "threat_level", "Categórico", "LOW / MEDIUM / HIGH / CRITICAL", "Target multiclase para clasificación supervisada."),
        ("21", "risk_score", "Float", "0.0 a 100.0 (media 62.72)", "Target continuo para Regresión Lineal (sin usar threat_level)."),
    ]
    _add_styled_table(
        doc,
        headers=("N°", "Variable", "Tipo", "Rango / Valores", "Rol Analítico y Significado C-UAS"),
        rows=dict_rows,
        col_widths_in=(0.35, 1.30, 0.80, 1.55, 2.90),
        font_size_pt=8.0,
    )

    _add_styled_table(
        doc,
        headers=("Dataset", "Brutos", "Duplicados", "Fuera de Envolvente", "Nulos Imputados", "Limpios Finales", "Distribución threat_level"),
        rows=[
            (
                "Principal (Lote 1)",
                "125,000",
                "3,750 (3.0 %)",
                "12,500 (10.0 %)",
                "8,750",
                "108,750",
                "MEDIUM: 40,395 · HIGH: 37,121 · LOW: 22,325 · CRITICAL: 8,909",
            ),
            (
                "Independiente (Lote 2)",
                "120,000",
                "3,600 (3.0 %)",
                "12,000 (10.0 %)",
                "8,400",
                "104,400",
                "MEDIUM: 38,902 · HIGH: 35,496 · LOW: 21,459 · CRITICAL: 8,543",
            ),
        ],
        col_widths_in=(1.15, 0.70, 0.85, 0.95, 0.85, 0.85, 1.55),
        font_size_pt=8.0,
    )

    # ------------------------------------------------------------------
    # Seccion 3
    # ------------------------------------------------------------------
    _add_h1(doc, "3. Fase 3: Preparación y Control Estricto de Data Leakage")
    _add_body(
        doc,
        "Todas las rutas de entrenamiento y exportación (02_crisp_dm_pipeline.py, 05_predictive_models_benchmark.py y 03_export_orange.py) "
        "comparten el módulo unificado data_mining/limpieza.py (función clean_telemetry()), garantizando paridad exacta entre Python y Orange:",
    )
    _add_bullets(
        doc,
        [
            ("1. Deduplicación exacta: ", "Eliminación de 3,750 filas repetidas en el lote principal (3,600 en el Lote 2)."),
            ("2. Normalización y rangos acotados: ", "Conversión de tokens corruptos (1,096 celdas en Lote 1) y valores físicamente imposibles de confianza o batería a NaN."),
            ("3. Filtrado de anomalías extremas: ", "Remoción de 12,500 filas fuera de la envolvente física C-UAS, conservando exactamente 108,750 registros limpios (104,400 en Lote 2)."),
            ("4. Partición estratificada antes del ajuste (Zero Data Leakage): ", "La división 80 % entrenamiento (87,000) / 20 % prueba (21,750) se realiza antes de ajustar imputadores (mediana/moda), StandardScaler, OrdinalEncoder u OneHotEncoder."),
            ("5. Aislamiento entre targets: ", "Al exportar aeroguard_regresion_riesgo.csv.gz para estimar risk_score en Orange, threat_level se marca como metadato (mS#) evitando fuga de información del target discreto al regresor."),
        ],
    )

    # ------------------------------------------------------------------
    # Seccion 4
    # ------------------------------------------------------------------
    _add_h1(doc, "4. Fases 4–6: Benchmark de los 6 Modelos Predictivos y Despliegue")
    _add_body(
        doc,
        "El script reproducible data_mining/05_predictive_models_benchmark.py entrena y evalúa los seis algoritmos solicitados sobre los 108,750 "
        "registros limpios y valida generalización ciega frente al Lote 2 (104,400 registros). En paralelo, los clasificadores y el regresor lineal "
        "fueron validados visualmente en Orange 3.41 (Sección 7).",
    )

    models_rows = [
        (
            "1. Regresión Lineal\n(LinearRegression)",
            "¿Cuál es el puntaje continuo de riesgo cinemático risk_score (0–100)?",
            "R² = 0.9356 · MAE = 4.24 · RMSE = 5.49\n(Orange CV 5 folds: R² = 0.927, RMSE = 5.808)",
            "R² = 0.9350 · MAE = 4.21 · RMSE = 5.47",
            "Integrado en API/UI para priorizar cola continua 0–100.",
        ),
        (
            "2. Regresión Logística\n(LogisticRegression)",
            "¿Probabilidad de violación crítica (HIGH/CRITICAL) y umbral F1 óptimo?",
            "ROC-AUC = 0.9689 · Umbral = 0.40 · F1 = 0.8821 · Prec = 0.8565 · Rec = 0.9094 · Brier = 0.0702 (Multiclase: 80.64 %)",
            "ROC-AUC = 0.9691 · F1 = 0.8820\n(Orange norm. 4 clases: AUC=0.947, CA=80.4 %)",
            "Integrado como calibrador binario (umbral 0.40). Descartado como multiclase frente a árboles.",
        ),
        (
            "3. K-Means (k = 4)\n(No supervisado)",
            "¿Qué perfiles cinemáticos de vuelo emergen sin etiquetas previas?",
            "Inercia = 124,517.6 · Silhouette = 0.2623 (sobre distancia, altitud y velocidad)",
            "Asignación en vivo por centroides físicos normalizados",
            "Integrado en API/UI y Orange (Scatter Plot por Cluster).",
        ),
        (
            "4. Árbol de Decisión\n(DecisionTree, depth=12)",
            "¿Qué reglas jerárquicas auditables clasifican threat_level?",
            "Accuracy = 94.23 % · F1(W) = 0.9422 · F1(Macro) = 0.9376",
            "Accuracy = 94.17 % · F1(W) = 0.9417\n(Orange: CA = 95.3 %, AUC = 0.991)",
            "Modelo secundario explicable (Tree Viewer en Orange).",
        ),
        (
            "5. Random Forest\n(100 / 12 árboles)",
            "¿Qué ensamble logra mayor precisión y estabilidad multiclase?",
            "Full (100): Acc = 95.95 % · F1 = 0.9595 · Macro = 0.9570\nRuntime (12): Acc = 95.08 % · F1 = 0.9507",
            "Full: 95.95 % · Runtime (12): 95.19 %\n(Orange Lote 2: CA = 95.4 %, AUC = 0.995)",
            "SELECCIONADO A PRODUCCIÓN: 862.4 KB JSON con 100.00 % paridad.",
        ),
        (
            "6. ARIMA (1, 1, 1)\n(Serie temporal)",
            "¿Cuántos picos diarios HIGH/CRITICAL habrá en los próximos 14 días?",
            "Split cronológico 243d/61d: AIC = 1897.79 · MAE = 10.09 · RMSE = 12.90 · MAPE = 6.77 %",
            "Horizonte 14 días: pico ~151.77 eventos/día (IC 95 %: 128.02–175.51)",
            "Integrado en /api/v1/predictions/forecast (en Python/statsmodels).",
        ),
    ]
    _add_styled_table(
        doc,
        headers=("Algoritmo", "Pregunta Predictiva", "Test Interno (20 %, n=21,750)", "Lote 2 / Validación Externa", "Decisión Productiva"),
        rows=models_rows,
        col_widths_in=(1.15, 1.35, 1.65, 1.45, 1.30),
        font_size_pt=7.8,
    )

    _add_h2(doc, "4.1 Perfiles Operativos Descubiertos por K-Means (k = 4)")
    kmeans_rows = [
        ("C3", "Aproximación Cercana al Perímetro", "469.9 m", "157.6 m", "8.8 m/s", "57.81 %", "25.67 %"),
        ("C1", "Sobrevuelo Elevado (Sobre Cota 120 m)", "1,067.3 m", "217.6 m", "23.7 m/s", "61.52 %", "24.45 %"),
        ("C0", "Tránsito Rápido Perimetral", "879.8 m", "72.2 m", "23.5 m/s", "43.57 %", "24.64 %"),
        ("C2", "Vuelo Distante / Baja Energía", "1,515.6 m", "132.1 m", "9.0 m/s", "6.78 %", "25.24 %"),
    ]
    _add_styled_table(
        doc,
        headers=("Clúster", "Etiqueta Táctica", "Dist. Media", "Alt. Media", "Vel. Media", "% HIGH/CRIT", "Partic."),
        rows=kmeans_rows,
        col_widths_in=(0.55, 2.25, 0.85, 0.85, 0.85, 0.85, 0.70),
        font_size_pt=8.2,
    )

    _add_callout(
        doc,
        "Criterio Técnico de Despliegue (Oracle Cloud <= 4 GiB RAM / ARM64 y x86_64):",
        "Random Forest (12 árboles compacto) supera en +14.44 puntos porcentuales a la Regresión Logística multiclase (95.08 % vs 80.64 %) "
        "porque el riesgo C-UAS obedece a interacciones no lineales (altitud > 120 m AND distancia < 150 m AND clase/patrón). "
        "Para evitar instalar scikit-learn, scipy o statsmodels en la imagen productiva de Oracle, todo el artefacto se exporta a "
        "predictive_models_artifact.json (862.4 KB), ejecutando inferencia en < 2 ms solo con Python estándar y NumPy.",
    )

    _add_h2(doc, "4.2 Reglas de Conocimiento Accionables (Fase 6 CRISP-DM)")
    _add_bullets(
        doc,
        [
            ("Proximidad y velocidad (n = 1,237): ", "Con distance_to_zone_m < 150 m, speed_ms > 20 m/s y patrón Directo o Evasivo, el 87.8 % resulta CRITICAL (frente a 8.2 % base)."),
            ("Techo civil 120 m y drones no comerciales (n = 20,747): ", "Con altitud > 120 m y clase diy_custom o fixed_wing, los niveles HIGH/CRITICAL suben a 69.9 % frente a 35.8 % (+34.1 pp)."),
            ("Filtrado de aves (n = 8,761): ", "El 100.0 % de los registros bird_false_pos corresponde a LOW, habilitando supresión automática de fatiga por falsos positivos."),
            ("Potencia radioeléctrica RF (n = 23,217): ", "Con señal > -50 dBm, la incidencia HIGH/CRITICAL aumenta a 53.2 % frente a 39.4 %."),
        ],
    )

    _add_figure(
        doc,
        FIGURES_DIR / "09_arima_pronostico_incursiones.png",
        "Figura 1 — Serie temporal diaria (304 días), split cronológico 80/20 (MAE = 10.09, RMSE = 12.90, MAPE = 6.77 %) y pronóstico ARIMA(1,1,1) a 14 días (pico esperado ~151.77 eventos/día).",
        subtitle="Evidencia analítica de Series Temporales ARIMA(1,1,1) — Ejecutada en Python/statsmodels y servida en /api/v1/predictions/forecast",
    )
    _add_figure(
        doc,
        FIGURES_DIR / "10_comparativa_6_modelos_resumen.png",
        "Figura 2 — Comparativa global de desempeño entre modelos de clasificación multiclase, probabilidad logística, regresión lineal R², K-Means y ARIMA(1,1,1) frente a la meta académica del 92 %.",
    )

    # ------------------------------------------------------------------
    # Seccion 5
    # ------------------------------------------------------------------
    _add_h1(doc, "5. Transformación de Datos Aplicada a AeroGuard")
    _add_body(
        doc,
        "Principio rector: «Transformar datos en decisiones es un proceso, no un evento». Un sensor en bruto no genera criterio operativo; "
        "atraviesa cuatro etapas arquitectónicas sustentadas por los cuatro pilares de la Gestión de Datos:",
    )
    _add_styled_table(
        doc,
        headers=("Etapa / Pilar", "Aplicación Concreta en AeroGuard", "Evidencia Trazable en Repositorio"),
        rows=[
            (
                "1. Datos Dispersos",
                "Tramas heterogéneas de sensores ópticos/YOLO (ai_service), espectro RF, radar cinemático, clima y polígonos restringidos; expuestas a pérdida de paquetes, nulos y duplicados.",
                "sensor_simulator/, 01_generate_dataset.py (125,000 filas brutas).",
            ),
            (
                "2. Gestión — Pilar 1:\nIntegración",
                "Ingesta unificada vía FastAPI REST, colas AMQP en RabbitMQ y función compartida clean_telemetry() entre entrenamiento Python y Orange.",
                "backend/app/api/v1/endpoints/sensors.py, data_mining/limpieza.py.",
            ),
            (
                "2. Gestión — Pilar 2:\nCalidad",
                "Rechazo HTTP 422 de NaN/Infinity y rangos físicos imposibles, deduplicación (3,750 filas), reemplazo de tokens corruptos (1,096) y control anti-fuga.",
                "predictions.py (StrictJsonRoute), 02_crisp_dm_pipeline.py.",
            ),
            (
                "2. Gestión — Pilar 3:\nMDM (Datos Maestros)",
                "Catálogos unívocos de drone_class, flight_pattern, sensor_id, geocercas PostGIS y taxonomía estandarizada de roles SOC.",
                "backend/app/models/models.py, 03_export_orange.py.",
            ),
            (
                "2. Gestión — Pilar 4:\nGobierno",
                "Control RBAC con JWT, auditoría inmutable, redacción automática de secretos en logs, Guardrails IN/OUT en Agentes IA y rigor explícito sobre datos sintéticos.",
                "security.py, audit_service.py, agent_guardrails.py.",
            ),
            (
                "3. Datos Confiables",
                "Repositorio limpio y tipado (108,750 registros principales + 104,400 Lote 2 en .csv/.csv.gz; PostGIS GiST en tiempo real y Qdrant embebido para RAG).",
                "data_mining/orange/*.csv.gz, deploy/compose.oracle.yml.",
            ),
            (
                "4. IA, Analítica,\nDashboards y Decisiones",
                "Consola predictiva y Agente LangGraph que entregan amenaza, risk_score, probabilidad logística, perfil K-Means y pronóstico ARIMA para decisión humana asistida.",
                "predictive_ml_service.py, agent_graph_service.py, dashboard.view.js.",
            ),
        ],
        col_widths_in=(1.45, 3.50, 1.95),
        font_size_pt=8.2,
    )

    # ------------------------------------------------------------------
    # Seccion 6
    # ------------------------------------------------------------------
    _add_h1(doc, "6. Matriz de Madurez Digital e IA Aplicada a AeroGuard (6 Dimensiones x 5 Niveles)")
    _add_body(
        doc,
        "Alineado con la evaluación TRL 4 (prototipo validado en laboratorio), se diagnostican las seis dimensiones organizacionales y tecnológicas "
        "en la escala estándar: 1. Inicial -> 2. Digitalización -> 3. Integración -> 4. Automatización -> 5. Organización Inteligente.",
    )
    maturity_rows = [
        (
            "1. Estrategia y Gobierno",
            "Nivel 3 (Consolidado)\nMeta -> Nivel 4",
            "Visión C-UAS documentada, KPIs verificados (>95 % Accuracy ML, 0 hallazgos Bandit), rigor sintético explícito y políticas de seguridad.",
            "Adoptar gobierno formal MLOps/LLMOps con SLA y reentrenamiento continuo en campo.",
        ),
        (
            "2. Personas y Cultura",
            "Nivel 3",
            "Roles RBAC definidos (Admin/Operator/Analyst), validación cruzada humano-IA en el SOC y guías de operación.",
            "Ejecutar pilotos con operadores C-UAS reales y retroalimentación de falsos positivos.",
        ),
        (
            "3. Procesos",
            "Nivel 3 (camino a 4)",
            "CRISP-DM reproducible, batería QA E2E, monitoreo Prometheus/Grafana, APScheduler para reportes/RAG y orquestación LangGraph.",
            "Conectar playbooks SOAR n8n activos y respuesta supervisada ante incidentes reales.",
        ),
        (
            "4. Datos",
            "Nivel 3",
            "PostGIS espacial + limpieza compartida sin data leakage (108,750 / 104,400 registros) + trazabilidad de corpus RAG en Qdrant.",
            "Ingesta continua multi-sensor física en streaming con linaje vivo.",
        ),
        (
            "5. Tecnología IA",
            "Nivel 3–4 (Avanzado)",
            "6 modelos predictivos (artefacto 862.4 KB en FastAPI) + Agente LangGraph (DeepSeek/fallback determinista), Qdrant RAG, Guardrails IN/OUT y MCP.",
            "Calibración adaptativa multimodal con sensores reales (TRL 5–6).",
        ),
        (
            "6. Valor de Negocio",
            "Nivel 2–3",
            "Filtrado del 100 % de aves simuladas (bird_false_pos -> LOW) y priorización cuantitativa de colas de riesgo.",
            "Medir reducción real de tiempos de reacción SOC en despliegue piloto controlado.",
        ),
    ]
    _add_styled_table(
        doc,
        headers=("Dimensión", "Nivel Actual", "Evidencia Comprobada en AeroGuard", "Ruta al Siguiente Nivel (4–5)"),
        rows=maturity_rows,
        col_widths_in=(1.35, 1.05, 2.75, 1.75),
        font_size_pt=8.2,
    )

    # ------------------------------------------------------------------
    # Seccion 7 (Orange 3.41 + 7 capturas reales)
    # ------------------------------------------------------------------
    doc.add_page_break()
    _add_h1(doc, "7. Sustentación y Evidencia Visual en Orange Data Mining 3.41")
    _add_body(
        doc,
        "Orange Data Mining 3.41.0 se integró como herramienta externa independiente para auditar visualmente el flujo CRISP-DM y demostrar que "
        "el desempeño no depende de una librería específica de Python. Al evaluar exactamente el mismo problema sobre el Lote 2 ciego "
        "(104,400 registros mediante Test on test data), Orange reprodujo Random Forest (CA = 0.954, AUC = 0.995) y evidenció por qué "
        "Regresión Logística multiclase cae (~0.804 CA normalizada) frente a fronteras cinemáticas no lineales.",
    )
    _add_bullets(
        doc,
        [
            ("Archivo principal listo para abrir: ", "data_mining/orange/AeroGuard_CRISP_DM_6Modelos.ows (18 widgets conectados: clasificación supervisada, normalizador LogReg, K-Means k=4 -> Scatter Plot y Regresión Lineal sobre risk_score)."),
            ("Acceso directo en el equipo: ", "Escritorio\\Ing\\Orange Data Mining.lnk (ejecuta Orange 3.41.0 en la carpeta data_mining/orange)."),
            ("Nota sobre ARIMA: ", "Orange 3 base está orientado a datos tabulares; la serie temporal ARIMA(1,1,1) se sustenta mediante statsmodels en Python (Figura 1) y el endpoint /api/v1/predictions/forecast."),
        ],
    )

    captures = [
        (
            CAPTURAS_DIR / "captura_01_canvas_completo.png",
            "7.1 Captura 1 — Lienzo Completo del Flujo CRISP-DM en Orange 3.41 (18 Widgets)",
            "Captura 1 — Vista completa de AeroGuard_CRISP_DM_6Modelos.ows en Orange Data Mining 3.41.0: carga de Lote 1 (108,750 filas), "
            "Lote 2 (104,400 filas) y dataset de regresión (risk_score), exploración EDA, Normalizar (LogReg), Árbol, Random Forest, "
            "Test and Score, Matriz de confusión, Visor del árbol, K-Means (k=4) -> Scatter Plot y Regresión lineal -> Test and Score (Regresión).",
        ),
        (
            CAPTURAS_DIR / "captura_02_archivo_entrenamiento.png",
            "7.2 Captura 2 — Carga y Tipado de Variables en Entrenamiento (Lote 1)",
            "Captura 2 — Widget Entrenamiento (File) cargando aeroguard_entrenamiento.csv.gz: 108,750 instancias, 13 features numéricas y "
            "categóricas, variable objetivo discreta threat_level (4 clases: CRITICAL, HIGH, LOW, MEDIUM) y 6 metadatos excluidos del modelo.",
        ),
        (
            CAPTURAS_DIR / "captura_03_eda_boxplot_ranking.png",
            "7.3 Captura 3 — Exploración EDA (Box Plot) y Ranking de Importancia (Rank)",
            "Captura 3 — Box Plot de distance_to_zone_m agrupado por threat_level (izquierda: ANOVA = 18067.773, p = 0.000; cercanía crítica "
            "de 261.3 ± 227.1 m frente a 1291.5 ± 498.7 m en LOW) junto a Rank (derecha: Gain Ratio y Gini encabezados por distance_to_zone_m, "
            "drone_class, speed_ms y flight_pattern).",
        ),
        (
            CAPTURAS_DIR / "captura_04_test_and_score_lote2.png",
            "7.4 Captura 4 — Evaluación Ciega en Lote 2 (Test on test data, n = 104,400)",
            "Captura 4 — Ventana de Test and Score en modo Test on test data sobre el Lote 2 independiente (104,400 registros): Random Forest "
            "(AUC = 0.995, CA = 0.954, F1 = 0.954), Árbol de decisión (AUC = 0.991, CA = 0.953, F1 = 0.953) y Regresión logística normalizada "
            "(AUC = 0.947, CA = 0.804, F1 = 0.804).",
        ),
        (
            CAPTURAS_DIR / "captura_05_matriz_confusion_y_arbol.png",
            "7.5 Captura 5 — Matriz de Confusión (Random Forest) y Reglas en Visor del Árbol",
            "Captura 5 — Matriz de confusión 4x4 de Random Forest sobre 104,400 casos del Lote 2 (izquierda, alta diagonal y mínima confusión "
            "entre niveles adyacentes) y jerarquía interpretable en Visor del árbol (derecha: 1,205 nodos, 603 hojas).",
        ),
        (
            CAPTURAS_DIR / "captura_06_kmeans_scatter.png",
            "7.6 Captura 6 — Segmentación No Supervisada K-Means (k = 4) y Scatter Plot",
            "Captura 6 — Widget k-Means configurado con k = 4, inicialización KMeans++ y normalización (izquierda), conectado al Scatter Plot "
            "de distance_to_zone_m vs altitude_m coloreado por Cluster C1..C4 (derecha), mostrando los cuatro regímenes operativos del espacio aéreo.",
        ),
        (
            CAPTURAS_DIR / "captura_07_regresion_lineal.png",
            "7.7 Captura 7 — Evaluación de Regresión Lineal Continua sobre risk_score",
            "Captura 7 — Test and Score (Regresión) con validación cruzada de 5 folds sobre aeroguard_regresion_riesgo.csv.gz: "
            "MSE = 33.732, RMSE = 5.808, MAE = 4.384 y R² = 0.927 al estimar el puntaje continuo risk_score (0–100).",
        ),
    ]

    for img_path, sub_title, cap_text in captures:
        _add_figure(
            doc,
            img_path,
            cap_text,
            width_in=6.3,
            subtitle=sub_title,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path


if __name__ == "__main__":
    generated = build_report()
    print(f"Documento generado correctamente: {generated} ({generated.stat().st_size:,} bytes)")
