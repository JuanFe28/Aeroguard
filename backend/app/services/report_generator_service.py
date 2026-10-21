"""
AeroGuard — Report Generator Service (ReportLab + OpenPyXL)
Generación física de reportes tácticos en PDF y hojas de cálculo Excel
sellados con hash criptográfico SHA-256 para auditoría y cadena de custodia.
Fase 2 - CODE: HU-02 ([CODE-02]).
"""

import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional

import structlog
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

logger = structlog.get_logger("AeroGuard-ReportGen")


class ReportGeneratorService:
    """Motor de compilación física de documentos analíticos y tácticos."""

    # Paleta táctica AeroGuard
    COLOR_PRIMARY   = colors.HexColor("#0A192F")   # Azul marino oscuro militar
    COLOR_ACCENT    = colors.HexColor("#00D4FF")   # Cyan táctico
    COLOR_DANGER    = colors.HexColor("#FF1744")   # Rojo crítico
    COLOR_WARNING   = colors.HexColor("#FF9100")   # Naranja alerta
    COLOR_SUCCESS   = colors.HexColor("#00E676")   # Verde seguro
    COLOR_TEXT_DARK = colors.HexColor("#1E293B")   # Slate oscuro
    COLOR_BG_LIGHT  = colors.HexColor("#F8FAFC")   # Fondo gris muy claro
    COLOR_BORDER    = colors.HexColor("#CBD5E1")   # Borde suave

    @staticmethod
    def compute_sha256(data_bytes: bytes) -> str:
        """Calcula el hash SHA-256 para garantizar la integridad y cadena de custodia."""
        return hashlib.sha256(data_bytes).hexdigest()

    @classmethod
    def get_default_dataset(cls, user_name: str = "Carlos Ramírez (Admin)") -> Dict[str, Any]:
        """Genera datos sintéticos de demostración; no consulta detecciones de la BD."""
        now = datetime.now(timezone.utc)
        report_id = f"REP-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

        from datetime import timedelta
        incursions = [
            {
                "id": "DET-BGA-402",
                "sensor": "CAM-BGA-NORTE-01",
                "zone": "Perímetro Seguridad UTS / Bucaramanga Centro",
                "lat": 7.1193,
                "lng": -73.1227,
                "alt": 145.0,
                "speed": 69.8,
                "heading": 182,
                "severity": "CRITICAL",
                "is_drone": True,
                "ai_confidence": 0.942,
                "timestamp": (now - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
            {
                "id": "DET-PLN-108",
                "sensor": "OPT-PALONEGRO-02",
                "zone": "Aeropuerto Palonegro (Área Crítica Pista)",
                "lat": 7.1265,
                "lng": -73.1848,
                "alt": 95.0,
                "speed": 48.2,
                "heading": 45,
                "severity": "HIGH",
                "is_drone": True,
                "ai_confidence": 0.885,
                "timestamp": (now - timedelta(minutes=7)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
            {
                "id": "DET-BOG-701",
                "sensor": "CAM-DORADO-01",
                "zone": "Aeropuerto El Dorado (Aproximación Sur)",
                "lat": 4.7082,
                "lng": -74.1350,
                "alt": 210.0,
                "speed": 82.5,
                "heading": 310,
                "severity": "CRITICAL",
                "is_drone": True,
                "ai_confidence": 0.965,
                "timestamp": (now - timedelta(minutes=14)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
            {
                "id": "DET-BGA-305",
                "sensor": "RADAR-SANTANDER-01",
                "zone": "Complejo Gubernamental Santander",
                "lat": 7.1210,
                "lng": -73.1180,
                "alt": 60.0,
                "speed": 22.1,
                "heading": 90,
                "severity": "MEDIUM",
                "is_drone": False,
                "ai_confidence": 0.310,
                "timestamp": (now - timedelta(minutes=25)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
            {
                "id": "DET-BOG-204",
                "sensor": "RF-CENTRAL-01",
                "zone": "Centro de Operaciones Bogotá",
                "lat": 4.7110,
                "lng": -74.0720,
                "alt": 45.0,
                "speed": 15.0,
                "heading": 15,
                "severity": "LOW",
                "is_drone": False,
                "ai_confidence": 0.120,
                "timestamp": (now - timedelta(minutes=42)).strftime("%Y-%m-%d %H:%M:%S UTC"),
            },
        ]

        return {
            "data_source": "synthetic_demo",
            "report_id": report_id,
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "operator": user_name,
            "organization": "Unidades Tecnológicas de Santander (UTS) — C-UAS AeroGuard",
            "kpis": {
                "total_flights": len(incursions),
                "geofence_violations": sum(1 for x in incursions if x["severity"] in ["CRITICAL", "HIGH"]),
                "max_altitude_m": max(x["alt"] for x in incursions),
                "top_sensor": "CAM-BGA-NORTE-01",
                "critical_threats": sum(1 for x in incursions if x["severity"] == "CRITICAL"),
            },
            "ai_verdict": (
                "UAV-402 mantiene rumbo sur a 145m sobrepasando el techo de 120m en la zona restringida "
                "de Bucaramanga Centro. La cinemática refleja vector de aproximación constante. "
                "Recomendación de ejemplo: verificar visualmente y notificar al responsable de seguridad."
            ),
            "incursions": incursions,
        }

    # ============================================================
    # Generación de PDF con ReportLab
    # ============================================================

    @classmethod
    def generate_pdf(cls, data: Optional[Dict[str, Any]] = None, operator: str = "Operador C-UAS") -> Tuple[bytes, str]:
        """
        Compila físicamente un PDF táctico con membrete UTS, KPIs,
        dictamen IA, tabla de incursiones y hash SHA-256 de integridad.
        """
        if not data:
            data = cls.get_default_dataset(user_name=operator)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Estilos personalizados
        title_style = ParagraphStyle(
            "AeroGuardTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=cls.COLOR_PRIMARY,
        )

        subtitle_style = ParagraphStyle(
            "AeroGuardSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#475569"),
        )

        kpi_num_style = ParagraphStyle(
            "AeroGuardKpiNum",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,  # Centro
            textColor=cls.COLOR_PRIMARY,
        )

        kpi_label_style = ParagraphStyle(
            "AeroGuardKpiLbl",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=1,
            textColor=colors.HexColor("#64748B"),
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=cls.COLOR_TEXT_DARK,
        )

        table_cell_mono = ParagraphStyle(
            "TableCellMono",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=cls.COLOR_TEXT_DARK,
        )

        verdict_style = ParagraphStyle(
            "VerdictStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        )

        elements = []

        # 1. Cabecera institucional UTS y AeroGuard
        header_table_data = [
            [
                Paragraph("<b>UNIDADES TECNOLÓGICAS DE SANTANDER (UTS)</b><br/>FACULTAD DE CIENCIAS NATURALES E INGENIERÍAS", subtitle_style),
                Paragraph(f"<b>REPORTE ACADÉMICO C-UAS</b><br/>ID: <font color='#00d4ff'>{data['report_id']}</font>", ParagraphStyle("RightH", parent=subtitle_style, alignment=2)),
            ]
        ]
        header_table = Table(header_table_data, colWidths=[340, 200])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(header_table)

        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=2, color=cls.COLOR_PRIMARY, spaceAfter=8))

        elements.append(Paragraph("AeroGuard — Detección experimental y monitoreo", title_style))
        if data.get("data_source") == "synthetic_demo":
            elements.append(Paragraph("DEMO — DATOS SINTÉTICOS. No acredita incidentes ni detecciones reales.", subtitle_style))
        elements.append(Paragraph(f"Emisión: {data['generated_at']} | Operador Responsable: <b>{data['operator']}</b>", subtitle_style))
        elements.append(Spacer(1, 12))

        # 2. Resumen Ejecutivo (KPI Cards en Tabla)
        kpis = data.get("kpis", {})
        kpi_data = [
            [
                Paragraph(str(kpis.get("total_flights", 0)), kpi_num_style),
                Paragraph(str(kpis.get("geofence_violations", 0)), ParagraphStyle("KRed", parent=kpi_num_style, textColor=cls.COLOR_DANGER)),
                Paragraph(f"{kpis.get('max_altitude_m', 0):.0f} m", kpi_num_style),
                Paragraph(str(kpis.get("top_sensor", "N/A")), ParagraphStyle("KSens", parent=kpi_num_style, fontSize=10, leading=14)),
            ],
            [
                Paragraph("Vuelos Detectados", kpi_label_style),
                Paragraph("Violaciones Geocerca", kpi_label_style),
                Paragraph("Altitud Máxima", kpi_label_style),
                Paragraph("Sensor Más Activo", kpi_label_style),
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), cls.COLOR_BG_LIGHT),
            ('BOX', (0,0), (-1,-1), 1, cls.COLOR_BORDER),
            ('INNERGRID', (0,0), (-1,-1), 0.5, cls.COLOR_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 12))

        # 3. Dictamen Táctico de IA (Sección 1.4 punto 3)
        ai_box_data = [
            [Paragraph("<b>🤖 DICTAMEN TÁCTICO DE INTELIGENCIA ARTIFICIAL (C-UAS AI ANALYST)</b>", ParagraphStyle("AITitle", parent=subtitle_style, fontName="Helvetica-Bold", textColor=cls.COLOR_PRIMARY))],
            [Paragraph(f'"{data.get("ai_verdict", "Sin dictamen registrado.")}"', verdict_style)]
        ]
        ai_box_table = Table(ai_box_data, colWidths=[540])
        ai_box_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),  # Azul claro
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#3B82F6")),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(ai_box_table)
        elements.append(Spacer(1, 12))

        # 4. Tabla Detallada de Incursiones (Sección 1.4 punto 4)
        elements.append(Paragraph("<b>Registro Detallado de Incursiones y Telemetría Operativa:</b>", subtitle_style))
        elements.append(Spacer(1, 4))

        headers = [
            Paragraph("ID Dron", table_header_style),
            Paragraph("Sensor / Zona", table_header_style),
            Paragraph("Coordenadas", table_header_style),
            Paragraph("Altitud", table_header_style),
            Paragraph("Velocidad", table_header_style),
            Paragraph("Severidad", table_header_style),
            Paragraph("Fecha / Hora", table_header_style),
        ]

        table_rows = [headers]
        for inc in data.get("incursions", []):
            sev = inc.get("severity", "LOW")
            sev_color = "#dc2626" if sev == "CRITICAL" else ("#ea580c" if sev == "HIGH" else "#16a34a")
            sev_badge = f"<font color='{sev_color}'><b>{sev}</b></font>"

            table_rows.append([
                Paragraph(inc.get("id", ""), table_cell_mono),
                Paragraph(f"<b>{inc.get('sensor','')}</b><br/><font color='#64748b'>{inc.get('zone','')}</font>", table_cell_style),
                Paragraph(f"{inc.get('lat',0):.4f}, {inc.get('lng',0):.4f}", table_cell_mono),
                Paragraph(f"{inc.get('alt',0):.0f} m", table_cell_style),
                Paragraph(f"{inc.get('speed',0):.1f} km/h", table_cell_style),
                Paragraph(sev_badge, table_cell_style),
                Paragraph(inc.get("timestamp", ""), table_cell_style),
            ])

        inc_table = Table(table_rows, colWidths=[65, 135, 80, 50, 55, 65, 90])
        inc_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), cls.COLOR_PRIMARY),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, cls.COLOR_BG_LIGHT]),
            ('GRID', (0,0), (-1,-1), 0.5, cls.COLOR_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(inc_table)
        elements.append(Spacer(1, 14))

        # 5. Pie de página criptográfico (Sección 1.4 punto 5)
        raw_signature_data = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        sha256_hash = cls.compute_sha256(raw_signature_data)

        footer_data = [
            [
                Paragraph(
                    f"<b>SELLO CRIPTOGRÁFICO DE INTEGRIDAD Y CADENA DE CUSTODIA (SHA-256):</b><br/>"
                    f"<font face='Courier' size='6.5' color='#0284c7'>{sha256_hash}</font><br/>"
                    f"<font size='6' color='#64748b'>Certificado expedido por motor AeroGuard C-UAS v1.1.0 — Validez pericial militar y académica.</font>",
                    table_cell_style,
                )
            ]
        ]
        footer_table = Table(footer_data, colWidths=[540])
        footer_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#94A3B8")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(KeepTogether(footer_table))

        # Construir documento
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        return pdf_bytes, sha256_hash

    # ============================================================
    # Generación de Excel con OpenPyXL
    # ============================================================

    @classmethod
    def generate_excel(cls, data: Optional[Dict[str, Any]] = None, operator: str = "Operador C-UAS") -> Tuple[bytes, str]:
        """
        Genera un archivo Excel (.xlsx) estructurado con la telemetría,
        análisis de amenazas y firma criptográfica SHA-256.
        """
        if not data:
            data = cls.get_default_dataset(user_name=operator)

        wb = Workbook()

        # Estilos Excel
        header_fill = PatternFill(start_color="0A192F", end_color="0A192F", fill_type="solid")
        kpi_fill    = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
        zebra_fill  = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        title_font  = Font(name="Calibri", size=14, bold=True, color="0A192F")
        bold_font   = Font(name="Calibri", size=10, bold=True, color="1E293B")
        regular_font= Font(name="Calibri", size=10, color="1E293B")
        mono_font   = Font(name="Consolas", size=9, color="0284C7")

        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # ====== Hoja 1: Incursiones y Telemetría ======
        ws1 = wb.active
        if ws1 is None:
            ws1 = wb.create_sheet(title="Telemetría e Incursiones")
        else:
            ws1.title = "Telemetría e Incursiones"

        # Título
        ws1["A1"] = "AEROGUARD C-UAS — REPORTE DE TELEMETRÍA E INCURSIONES"
        if data.get("data_source") == "synthetic_demo":
            ws1["A1"].value += " — DEMO: DATOS SINTÉTICOS"
        ws1["A1"].font = title_font
        ws1["A2"] = f"Generado: {data['generated_at']} | Operador: {data['operator']} | ID: {data['report_id']}"
        ws1["A2"].font = bold_font

        # Encabezados de tabla
        cols = [
            "ID Detección", "Sensor", "Zona Restringida",
            "Latitud", "Longitud", "Altitud (m)", "Velocidad (km/h)",
            "Rumbo (°)", "Severidad", "Dron Confirmado (IA)", "Confianza IA (%)", "Fecha / Hora (UTC)"
        ]

        row_idx = 4
        for col_idx, text in enumerate(cols, 1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=text)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

        # Filas de datos
        for inc in data.get("incursions", []):
            row_idx += 1
            row_vals = [
                inc.get("id"),
                inc.get("sensor"),
                inc.get("zone"),
                inc.get("lat"),
                inc.get("lng"),
                inc.get("alt"),
                inc.get("speed"),
                inc.get("heading"),
                inc.get("severity"),
                "SÍ" if inc.get("is_drone") else "NO",
                round(inc.get("ai_confidence", 0) * 100, 1),
                inc.get("timestamp"),
            ]
            for col_idx, val in enumerate(row_vals, 1):
                c = ws1.cell(row=row_idx, column=col_idx, value=val)
                c.font = mono_font if col_idx in [1, 4, 5] else regular_font
                c.border = thin_border
                c.alignment = Alignment(horizontal="center" if col_idx in [1, 4, 5, 6, 7, 8, 9, 10, 11] else "left")
                if row_idx % 2 == 0:
                    c.fill = zebra_fill

        # Ajuste de anchos de columna
        for col in ws1.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws1.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # ====== Hoja 2: Resumen Ejecutivo y Cadena de Custodia ======
        ws2 = wb.create_sheet(title="Resumen y Auditoría")
        ws2["A1"] = "RESUMEN EJECUTIVO Y FIRMA CRIPTOGRÁFICA"
        ws2["A1"].font = title_font

        kpis = data.get("kpis", {})
        summary_rows = [
            ("ID del Reporte", data["report_id"]),
            ("Institución", data["organization"]),
            ("Operador Solicitante", data["operator"]),
            ("Fecha y Hora de Emisión", data["generated_at"]),
            ("Vuelos Monitoreados", kpis.get("total_flights", 0)),
            ("Violaciones de Geocerca", kpis.get("geofence_violations", 0)),
            ("Amenazas Críticas", kpis.get("critical_threats", 0)),
            ("Altitud Máxima (m)", kpis.get("max_altitude_m", 0)),
            ("Sensor con Mayor Actividad", kpis.get("top_sensor", "N/A")),
            ("Dictamen IA", data.get("ai_verdict", "N/A")),
        ]

        r_start = 3
        for label, val in summary_rows:
            c1 = ws2.cell(row=r_start, column=1, value=label)
            c2 = ws2.cell(row=r_start, column=2, value=val)
            c1.font = bold_font
            c1.fill = kpi_fill
            c1.border = thin_border
            c2.font = regular_font
            c2.border = thin_border
            r_start += 1

        # Firma SHA-256
        raw_signature_data = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        sha256_hash = cls.compute_sha256(raw_signature_data)

        r_start += 2
        ws2.cell(row=r_start, column=1, value="HASH SHA-256 (INTEGRIDAD)").font = bold_font
        ws2.cell(row=r_start, column=2, value=sha256_hash).font = mono_font

        ws2.column_dimensions["A"].width = 30
        ws2.column_dimensions["B"].width = 75

        # Guardar en buffer
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_bytes = excel_buffer.getvalue()

        return excel_bytes, sha256_hash


# Instancia singleton
report_generator_service = ReportGeneratorService()
