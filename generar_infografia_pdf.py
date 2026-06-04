"""
generar_infografia_pdf.py
=========================
Genera la infografía profesional del proyecto Tareo PECEPE en PDF.
Ejecutar:  python generar_infografia_pdf.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import (
    HexColor, white, black, Color
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak,
)
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas as pdfgen_canvas
import io, datetime

# ── COLORES ──────────────────────────────────────────────────────────────────
AZUL_OSC  = HexColor("#0F2A6B")
AZUL      = HexColor("#1F4E9B")
AZUL_MED  = HexColor("#2563EB")
AZUL_CL   = HexColor("#DBEAFE")
AZUL_BG   = HexColor("#EFF6FF")
VERDE     = HexColor("#059669")
VERDE_CL  = HexColor("#D1FAE5")
AMBAR     = HexColor("#D97706")
AMBAR_CL  = HexColor("#FDE68A")
ROJO      = HexColor("#DC2626")
ROJO_CL   = HexColor("#FEE2E2")
MORADO    = HexColor("#7C3AED")
MORADO_CL = HexColor("#EDE9FE")
GRIS_OSC  = HexColor("#374151")
GRIS_MED  = HexColor("#6B7280")
GRIS_CL   = HexColor("#F9FAFB")
BORDE     = HexColor("#E5E7EB")
BLANCO    = white
TEAL      = HexColor("#0891B2")
TEAL_CL   = HexColor("#CFFAFE")
DARK_BG   = HexColor("#0F172A")

# ── ESTILOS DE TEXTO ─────────────────────────────────────────────────────────
def _s(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9, leading=13, textColor=GRIS_OSC)
    base.update(kw)
    return ParagraphStyle(name, **base)

S = {
    "h_port":   _s("hp",  fontName="Helvetica-Bold", fontSize=26, textColor=BLANCO, leading=30, spaceAfter=4),
    "sub_port": _s("sp",  fontName="Helvetica",      fontSize=12, textColor=HexColor("#93C5FD"), leading=16),
    "desc_port":_s("dp",  fontName="Helvetica",      fontSize=9.5,textColor=HexColor("#CBD5E1"), leading=14),
    "sec":      _s("sec", fontName="Helvetica-Bold", fontSize=12, textColor=AZUL, spaceBefore=14, spaceAfter=6),
    "card_h":   _s("ch",  fontName="Helvetica-Bold", fontSize=8,  textColor=GRIS_MED, spaceAfter=4),
    "titulo":   _s("t",   fontName="Helvetica-Bold", fontSize=9,  textColor=GRIS_OSC, spaceAfter=2),
    "normal":   _s("n",   fontSize=8.5, leading=12.5),
    "small":    _s("sm",  fontSize=7.5, textColor=GRIS_MED, leading=11),
    "mono":     _s("mo",  fontName="Courier", fontSize=7.5, textColor=HexColor("#1E40AF"), leading=11),
    "mono_dk":  _s("mdk", fontName="Courier", fontSize=7.5, textColor=HexColor("#6EE7B7"), leading=11),
    "kpi_num":  _s("kn",  fontName="Helvetica-Bold", fontSize=22, leading=24, textColor=AZUL, alignment=TA_CENTER),
    "kpi_lbl":  _s("kl",  fontSize=7.5, textColor=GRIS_MED, alignment=TA_CENTER, leading=10),
    "tab_n":    _s("tn",  fontName="Helvetica-Bold", fontSize=9, textColor=GRIS_OSC, spaceAfter=3),
    "tab_d":    _s("td",  fontSize=7.8, textColor=GRIS_MED, leading=11.5),
    "badge":    _s("bd",  fontName="Helvetica-Bold", fontSize=7, textColor=AZUL),
    "center":   _s("ctr", fontSize=8.5, alignment=TA_CENTER, leading=12),
    "rol_n":    _s("rn",  fontName="Helvetica-Bold", fontSize=10, textColor=AZUL),
    "footer":   _s("ft",  fontSize=7.5, textColor=HexColor("#94A3B8"), alignment=TA_CENTER),
}

W, H = A4  # 595.27 x 841.89 pt
MARGIN = 1.8 * cm


# ── FLOWABLES PERSONALIZADOS ──────────────────────────────────────────────────

class ColorRect(Flowable):
    """Rectángulo de color sólido."""
    def __init__(self, w, h, color, radius=4):
        super().__init__()
        self.w, self.h, self.color, self.radius = w, h, color, radius
        self.width = w

    def wrap(self, *args):
        return self.w, self.h

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.w, self.h, self.radius, fill=1, stroke=0)


class PortadaHeader(Flowable):
    """Cabecera azul de portada."""
    def __init__(self, page_w, page_h):
        super().__init__()
        self.pw, self.ph = page_w, page_h

    def wrap(self, *args):
        return self.pw, 0

    def draw(self):
        c = self.canv
        # Gradiente simulado con tres rectángulos
        for i, col in enumerate([AZUL_OSC, AZUL, AZUL_MED]):
            c.setFillColor(col)
            seg = self.pw / 3
            c.rect(i * seg, -5, seg + 2, 230, fill=1, stroke=0)
        # Orbe decorativo
        c.setFillColor(HexColor("#1D4ED8"))
        c.circle(self.pw - 60, 150, 80, fill=1, stroke=0)
        c.setFillColor(HexColor("#2563EB"))
        c.circle(self.pw - 80, 90, 50, fill=1, stroke=0)


class SeccionTitulo(Flowable):
    """Línea de sección con ícono cuadrado azul."""
    def __init__(self, texto, icono="▶", page_w=None):
        super().__init__()
        self.texto = texto
        self.icono = icono
        self.pw = page_w or (W - 2 * MARGIN)

    def wrap(self, *args):
        return self.pw, 24

    def draw(self):
        c = self.canv
        # Cuadrado ícono
        c.setFillColor(AZUL)
        c.roundRect(0, 2, 20, 20, 4, fill=1, stroke=0)
        c.setFillColor(BLANCO)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(10, 7, self.icono)
        # Texto
        c.setFillColor(AZUL)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(26, 6, self.texto)
        # Línea
        c.setStrokeColor(AZUL_CL)
        c.setLineWidth(1.5)
        c.line(0, 0, self.pw, 0)


class BarraTramos(Flowable):
    """Barra visual de tramos de horas."""
    def __init__(self, w=380):
        super().__init__()
        self.bw = w

    def wrap(self, *args):
        return self.bw, 28

    def draw(self):
        c = self.canv
        segs = [
            (0.615, VERDE,   "Normal ≤ 8h"),
            (0.154, AMBAR,   "25%"),
            (0.231, ROJO,    "35% +"),
        ]
        x = 0
        for pct, col, lbl in segs:
            sw = self.bw * pct
            c.setFillColor(col)
            c.roundRect(x, 8, sw - 1, 18, 3, fill=1, stroke=0)
            c.setFillColor(BLANCO)
            c.setFont("Helvetica-Bold", 7)
            cx = x + sw / 2
            c.drawCentredString(cx, 14, lbl)
            x += sw


class FlujoPasos(Flowable):
    """Diagrama de flujo horizontal con 6 pasos."""
    PASOS = [
        ("1", "Sistema\nAsistencia", "xlsx crudo"),
        ("2", "Cargar\n& Parsear", "auto-detecta\ncabecera"),
        ("3", "Condiciones\nTTHH", "Corrido·12h\nDesc·Aum"),
        ("4", "Cálculo\nTTHH", "Motor\nRR.HH."),
        ("5", "Aprobación", "por grupo\npor supervisor"),
        ("6", "Reporte\nFinal", "18 columnas\nxlsx+csv"),
    ]

    def __init__(self, w=460):
        super().__init__()
        self.fw = w

    def wrap(self, *args):
        return self.fw, 72

    def draw(self):
        c = self.canv
        n = len(self.PASOS)
        bw = self.fw / n
        arrow_w = 10
        box_w = bw - arrow_w - 2

        for i, (num, titulo, sub) in enumerate(self.PASOS):
            x = i * bw
            # Caja
            c.setFillColor(AZUL_BG)
            c.setStrokeColor(AZUL_CL)
            c.setLineWidth(0.8)
            c.roundRect(x, 10, box_w, 58, 5, fill=1, stroke=1)
            # Círculo número
            c.setFillColor(AZUL)
            c.circle(x + box_w / 2, 60, 9, fill=1, stroke=0)
            c.setFillColor(BLANCO)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x + box_w / 2, 57, num)
            # Título
            c.setFillColor(AZUL)
            c.setFont("Helvetica-Bold", 7)
            for j, line in enumerate(titulo.split("\n")):
                c.drawCentredString(x + box_w / 2, 42 - j * 10, line)
            # Sub
            c.setFillColor(GRIS_MED)
            c.setFont("Helvetica", 6.5)
            for j, line in enumerate(sub.split("\n")):
                c.drawCentredString(x + box_w / 2, 24 - j * 9, line)
            # Flecha
            if i < n - 1:
                ax = x + box_w + 1
                ay = 39
                c.setFillColor(AZUL_MED)
                c.setStrokeColor(AZUL_MED)
                c.setLineWidth(1.5)
                c.line(ax, ay, ax + arrow_w - 3, ay)
                c.setFillColor(AZUL_MED)
                pts = [ax + arrow_w - 3, ay + 4,
                       ax + arrow_w - 3, ay - 4,
                       ax + arrow_w + 1, ay]
                c.setLineWidth(0)
                path = c.beginPath()
                path.moveTo(pts[0], pts[1])
                path.lineTo(pts[2], pts[3])
                path.lineTo(pts[4], pts[5])
                path.close()
                c.drawPath(path, fill=1, stroke=0)


# ── HELPERS DE TABLA ─────────────────────────────────────────────────────────

def _tabla(data, col_widths, style_extra=None, hdr_color=AZUL_BG, row_shade=True):
    base_style = [
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  8),
        ("FONTSIZE",    (0, 1), (-1, -1), 7.5),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("BACKGROUND",  (0, 0), (-1, 0),  hdr_color),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BLANCO, GRIS_CL] if row_shade else [BLANCO]),
        ("ALIGN",       (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",        (0, 0), (-1, -1), 0.5, BORDE),
        ("ROWPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0,0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]
    if style_extra:
        base_style.extend(style_extra)
    return Table(data, colWidths=col_widths, style=TableStyle(base_style))


def _p(txt, style="normal", **kw):
    s = S.get(style, S["normal"])
    if kw:
        s = ParagraphStyle("_", parent=s, **kw)
    return Paragraph(str(txt), s)


def _badge_txt(txt, color=AZUL):
    return f'<font color="{color.hexval() if hasattr(color,"hexval") else color}"><b> {txt} </b></font>'


def _hr():
    return HRFlowable(width="100%", thickness=1, color=BORDE, spaceAfter=6, spaceBefore=6)


# ── CONSTRUCTOR DEL PDF ───────────────────────────────────────────────────────

def build_pdf(output_path: str) -> None:
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.8 * cm, bottomMargin=1.5 * cm,
    )
    content_w = W - 2 * MARGIN

    # ── Plantilla de página ─────────────────────────────────────────────────
    def _header_footer(c, doc):
        c.saveState()
        if doc.page > 1:
            c.setFillColor(AZUL)
            c.rect(0, H - 0.6 * cm, W, 0.6 * cm, fill=1, stroke=0)
            c.setFillColor(BLANCO)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(MARGIN, H - 0.42 * cm, "pecepe.  ·  Tareo de Operaciones")
            c.setFont("Helvetica", 7)
            c.drawRightString(W - MARGIN, H - 0.42 * cm, f"Página {doc.page}")
        # Footer
        c.setFillColor(DARK_BG)
        c.rect(0, 0, W, 0.9 * cm, fill=1, stroke=0)
        c.setFillColor(HexColor("#94A3B8"))
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(
            W / 2, 0.32 * cm,
            "© APLICACIONES — DONET 2026  ·  Python 3.12 · Streamlit · Supabase · Render · Plotly"
        )
        c.restoreState()

    frame = Frame(MARGIN, 0.9 * cm, content_w, H - 1.5 * cm, id="main")
    tmpl = PageTemplate(id="main", frames=[frame], onPage=_header_footer)
    doc.addPageTemplates([tmpl])

    story = []
    cw = content_w  # ancho útil
    half = (cw - 0.4 * cm) / 2

    # ════════════════════════════════════════════════════════════════════════
    # PÁGINA 1 — PORTADA
    # ════════════════════════════════════════════════════════════════════════

    # Bloque portada (tabla con fondo azul)
    port_data = [[
        Table([
            [_p("pecepe.", "h_port")],
            [_p("Aplicativo de Tareo de Operaciones", "sub_port")],
            [Spacer(1, 4)],
            [_p(
                "Sistema web colaborativo de gestión de horas que automatiza el "
                "cálculo de TTHH, horas extras estratificadas y genera el reporte "
                "corporativo de operaciones con validación multi-supervisor en tiempo real.",
                "desc_port"
            )],
            [Spacer(1, 12)],
            [_p(
                "🐍 Python 3.12  ·  ⚡ Streamlit  ·  🐘 PostgreSQL / Supabase  "
                "·  ☁️ Render  ·  📊 Plotly  ·  📋 openpyxl  ·  🔒 SHA-256",
                style="normal",
                textColor=HexColor("#CBD5E1"), fontSize=8
            )],
        ], colWidths=[cw - 1.6 * cm], style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#00000000")),
            ("TOPPADDING",  (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0,0), (-1, -1), 3),
        ]))
    ]]
    port_tbl = Table(port_data, colWidths=[cw], style=TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL),
        ("TOPPADDING",    (0, 0), (-1, -1), 24),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
        ("LEFTPADDING",   (0, 0), (-1, -1), 22),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 22),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [10, 10, 10, 10]),
    ]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(port_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # KPIs
    story.append(SeccionTitulo("Métricas del Proyecto", "★", cw))
    story.append(Spacer(1, 6))

    kpi_col = (cw - 0.9 * cm) / 4
    kpi_data = [[
        Table([[_p("160",   "kpi_num", textColor=AZUL)],   [_p("Registros por jornada",   "kpi_lbl")]], colWidths=[kpi_col - 4]),
        Table([[_p("159/160","kpi_num",textColor=VERDE)],  [_p("Coincidencia reporte real","kpi_lbl")]], colWidths=[kpi_col - 4]),
        Table([[_p("6",     "kpi_num", textColor=AMBAR)],  [_p("Pestañas funcionales",     "kpi_lbl")]], colWidths=[kpi_col - 4]),
        Table([[_p("7",     "kpi_num", textColor=MORADO)], [_p("Supervisores concurrentes","kpi_lbl")]], colWidths=[kpi_col - 4]),
    ]]
    story.append(Table(kpi_data, colWidths=[kpi_col] * 4, style=TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BLANCO),
        ("BOX",           (0, 0), (0, 0),   0.8, BORDE),
        ("BOX",           (1, 0), (1, 0),   0.8, BORDE),
        ("BOX",           (2, 0), (2, 0),   0.8, BORDE),
        ("BOX",           (3, 0), (3, 0),   0.8, BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ROUNDEDCORNERS",(0,0),  (-1,-1),  [8]*4),
    ])))
    story.append(Spacer(1, 0.4 * cm))

    # Flujo de datos
    story.append(SeccionTitulo("Flujo de Datos — De la marcación al reporte final", "→", cw))
    story.append(Spacer(1, 6))
    flujo_tbl = Table([[FlujoPasos(cw)]], colWidths=[cw], style=TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BLANCO),
        ("BOX",           (0, 0), (-1, -1), 0.8, BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(flujo_tbl)

    # ════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — MÓDULOS + MOTOR CÁLCULO
    # ════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Spacer(1, 0.3 * cm))

    # Módulos — 6 pestañas en tabla 3×2
    story.append(SeccionTitulo("Módulos de la Aplicación — 6 Pestañas", "⬡", cw))
    story.append(Spacer(1, 6))

    def _tab_cell(icono, nombre, desc, quien, color_top):
        inner = Table([
            [_p(icono, fontSize=16, leading=18, spaceBefore=0)],
            [_p(nombre, "tab_n")],
            [_p(desc, "tab_d")],
            [_p(f"◉ {quien}", fontSize=7, textColor=AZUL, fontName="Helvetica-Bold")],
        ], colWidths=[half / 3 * 3 - 0.4 * cm], style=TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return Table([[inner]], colWidths=[half], style=TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), BLANCO),
            ("BOX",           (0, 0), (-1, -1), 0.8, BORDE),
            ("TOPPADDING",    (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("LINEABOVE",     (0, 0), (-1, 0),  3.5, color_top),
        ]))

    tabs_row1 = [
        _tab_cell("📥", "1. Cargar",
                  "Sube el xlsx del sistema. Auto-detecta cabecera, normaliza columnas y procesa hasta 160 registros. Botón reinicio para nueva jornada.",
                  "Solo Coordinador", AZUL),
        _tab_cell("🧮", "2. Condiciones / TTHH",
                  "Editor masivo e individual por grupo. Corrido, Teórico 12h, Refrigerio, Descuento/Aumento extra, Jornada noche. Recalcula en tiempo real.",
                  "Coordinador + Supervisores", VERDE),
    ]
    tabs_row2 = [
        _tab_cell("✅", "3. Aprobación",
                  "Supervisor revisa TTHH de su grupo y aprueba. Panel de avance. Solo lo aprobado pasa al reporte final. Aprobación masiva o individual.",
                  "Coordinador + Supervisores", AMBAR),
        _tab_cell("📤", "4. Reporte Final",
                  "Genera REPORTE_OPERACIONES con 18 columnas formato corporativo. Descarga Excel (Calibri azul) y CSV. KPIs de horas totales, 25% y 35%.",
                  "Solo Coordinador", MORADO),
    ]
    tabs_row3 = [
        _tab_cell("📊", "Dashboard",
                  "7 gráficos Plotly interactivos con filtros. Sección A: tareo original (turnos, registros, condiciones, marcación). Sección B: TTHH, horas, aprobación.",
                  "Coordinador + Supervisores", TEAL),
        _tab_cell("📱", "Compartir (WhatsApp)",
                  "Resumen y reporte formateado con emojis. Botón verde abre WhatsApp listo para enviar. Descarga Excel adjuntable. Instrucciones export PNG.",
                  "Coordinador + Supervisores", ROJO),
    ]

    gap = 0.4 * cm
    tabs_tbl = Table(
        [tabs_row1, [Spacer(1, 5), Spacer(1, 5)],
         tabs_row2, [Spacer(1, 5), Spacer(1, 5)],
         tabs_row3],
        colWidths=[half, half],
        style=TableStyle([("LEFTPADDING", (0,0),(-1,-1), 0),
                          ("RIGHTPADDING",(0,0),(-1,-1), gap),
                          ("TOPPADDING",  (0,0),(-1,-1), 0),
                          ("BOTTOMPADDING",(0,0),(-1,-1), 0),
                          ]))
    story.append(tabs_tbl)
    story.append(Spacer(1, 0.4 * cm))

    # Motor de Cálculo
    story.append(SeccionTitulo("Motor de Cálculo — Reglas RR.HH. (tareo_core.py)", "⚙", cw))
    story.append(Spacer(1, 6))

    reglas_data = [
        ["Campo", "Regla / Descripción"],
        ["Horas Marcación",   "SALIDA − ENTRADA (decimal). Cruce de medianoche: si SALIDA ≤ ENTRADA → +24 h automático"],
        ["Refrigerio (45 min)", "Se descuenta SIEMPRE, SALVO: grupo en lista sin refrigerio (E, PCP, N, 5) · OBS = 'C' · OBS = '12'"],
        ["Teórico 12h",       "Si OBS = '12' → TTHH = 12.0 h exactas. Horario DÍA: 07:00–19:00. NOCHE: 19:00–07:00 o 20:00–08:00"],
        ["Corrido (C)",       "Sin descuento de refrigerio. Horario real de entrada/salida sin ajuste"],
        ["Descuento extra",   "−1, −2 o −3 horas adicionales restadas al bruto de marcación"],
        ["Aumento extra",     "+1, +2 o +3 horas adicionales sumadas al bruto de marcación"],
        ["TTHH final",        "max(0, HORAS_MARCACION − refrigerio − descuento + aumento) · si Teórico12 → 12.0 h fijo"],
    ]
    story.append(_tabla(reglas_data,
                        [2.8 * cm, cw - 2.8 * cm],
                        hdr_color=AZUL_BG))
    story.append(Spacer(1, 8))

    # Tramos
    tramos_data = [
        ["Tramo", "Rango", "Color", "Descripción"],
        ["Hora Normal", "0 → 8 h",   "■ Verde",  "Jornada base. min(TTHH, 8.0)"],
        ["Hora 25%",    "8 → 10 h",  "■ Ámbar",  "Extra tope. min(max(TTHH−8, 0), 2.0)"],
        ["Hora 35%",    "> 10 h",    "■ Rojo",   "Extra alto. max(TTHH−10, 0)"],
        ["Hora 100%",   "dom/feriado","■ Morado", "Manual — no calculado automáticamente"],
        ["BONO HH",     "especial",  "■ Gris",   "Manual — ingreso posterior"],
    ]
    cols_t = [2.3 * cm, 2.0 * cm, 1.8 * cm, cw - 6.1 * cm]
    story.append(_tabla(tramos_data, cols_t,
        style_extra=[
            ("TEXTCOLOR", (2, 1), (2, 1), VERDE),
            ("TEXTCOLOR", (2, 2), (2, 2), AMBAR),
            ("TEXTCOLOR", (2, 3), (2, 3), ROJO),
            ("TEXTCOLOR", (2, 4), (2, 4), MORADO),
            ("TEXTCOLOR", (2, 5), (2, 5), GRIS_MED),
            ("FONTNAME",  (2, 1), (2, 5), "Helvetica-Bold"),
        ],
        hdr_color=AZUL_BG))
    story.append(Spacer(1, 6))
    story.append(BarraTramos(cw))

    # ════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — ROLES + ARQUITECTURA + DB
    # ════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Spacer(1, 0.3 * cm))

    # Roles y permisos
    story.append(SeccionTitulo("Roles y Control de Acceso", "👤", cw))
    story.append(Spacer(1, 6))

    def _perm_ok(txt): return _p(f"✔  {txt}", fontSize=7.8, textColor=VERDE)
    def _perm_no(txt): return _p(f"✘  {txt}", fontSize=7.8, textColor=GRIS_MED)

    rol_coord = Table([
        [_p("👑  Coordinador", "rol_n")],
        [_p("donet  ·  donet2026", "small", fontName="Courier")],
        [Spacer(1, 4)],
        [_perm_ok("Cargar / reiniciar tareo del sistema")],
        [_perm_ok("Editar condiciones de TODOS los grupos")],
        [_perm_ok("Aprobar / desaprobar cualquier grupo")],
        [_perm_ok("Generar y descargar el reporte final")],
        [_perm_ok("Dashboard completo (todos los grupos)")],
        [_perm_ok("Compartir reporte final por WhatsApp")],
        [_perm_ok("Configurar reglas globales (sidebar)")],
        [_perm_ok("Gestión de usuarios — crear/editar/borrar")],
    ], colWidths=[half - 0.4 * cm], style=TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BLANCO),
        ("BOX",           (0, 0), (-1, -1), 0.8, BORDE),
        ("LINEABOVE",     (0, 0), (-1, 0),  3, AZUL),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
    ]))

    rol_sup = Table([
        [_p("🦺  Supervisor de Grupo", "rol_n", textColor=VERDE)],
        [_p("sup_N · sup_E · sup_PCP · sup_1…5", "small", fontName="Courier")],
        [Spacer(1, 4)],
        [_perm_no("Cargar / reiniciar tareo")],
        [_perm_ok("Editar condiciones de  su grupo")],
        [_perm_ok("Aprobar / desaprobar  su grupo")],
        [_perm_no("Reporte final completo")],
        [_perm_ok("Dashboard filtrado a  su grupo")],
        [_perm_ok("Compartir resumen de su grupo WhatsApp")],
        [_perm_no("Configurar reglas globales")],
        [_perm_no("Gestión de usuarios")],
    ], colWidths=[half - 0.4 * cm], style=TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), BLANCO),
        ("BOX",           (0, 0), (-1, -1), 0.8, BORDE),
        ("LINEABOVE",     (0, 0), (-1, 0),  3, VERDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
    ]))

    story.append(Table([[rol_coord, rol_sup]], colWidths=[half, half], style=TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (0, -1),  6),
        ("RIGHTPADDING",  (1, 0), (1, -1),  0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ])))

    story.append(Spacer(1, 0.4 * cm))

    # Arquitectura técnica + Modo Dual
    story.append(SeccionTitulo("Arquitectura Técnica", "🏗", cw))
    story.append(Spacer(1, 6))

    stack_data = [
        ["Capa", "Tecnología", "Versión", "Función"],
        ["Lenguaje",   "Python",           "3.12",   "Base completa del proyecto"],
        ["UI / Web",   "Streamlit",        "≥ 1.40", "Dashboard responsivo — PC, móvil, tablet"],
        ["Datos",      "pandas",           "≥ 2.0",  "DataFrames — carga, cálculo, exportación"],
        ["Excel",      "openpyxl",         "≥ 3.1",  "Lectura/escritura xlsx con formato corporativo"],
        ["Gráficos",   "Plotly",           "≥ 5.0",  "7 gráficos interactivos — descarga PNG nativa"],
        ["ORM / DB",   "SQLAlchemy",       "≥ 2.0",  "Acceso PostgreSQL · NullPool para Supabase"],
        ["Driver DB",  "psycopg2-binary",  "≥ 2.9",  "Conector PostgreSQL con soporte SSL"],
        ["Base datos", "Supabase",         "PG 17.6","PostgreSQL cloud · 3 tablas (usuarios/config/tareo)"],
        ["Hosting",    "Render",           "Free",   "Deploy automático en push a main · Python 3.12.7"],
        ["Autenticación","SHA-256 + salt", "—",      "Contraseñas nunca en claro · sal 16 chars hex"],
        ["VCS",        "Git / GitHub",     "—",      "Control de versiones · auto-deploy Render"],
    ]
    cols_s = [2.0 * cm, 2.6 * cm, 1.7 * cm, cw - 6.3 * cm]
    story.append(_tabla(stack_data, cols_s, hdr_color=AZUL_BG))
    story.append(Spacer(1, 8))

    # Modo dual
    dual_data = [[
        Table([
            [_p("🌐  Modo Online — Supabase", "titulo", textColor=AZUL)],
            [_p("Con DATABASE_URL configurada → usa PostgreSQL en Supabase. "
                "Persistencia compartida entre todos los supervisores. "
                "Escritura por subconjunto (UPDATE WHERE id IN grupo). "
                "SSL requerido. Multi-usuario concurrente sin conflictos.", "normal")],
        ], colWidths=[half - 0.4 * cm], style=TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), AZUL_BG),
            ("BOX",           (0,0), (-1,-1), 0.8, AZUL_CL),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ])),
        Table([
            [_p("💾  Modo Offline — Archivos locales", "titulo")],
            [_p("Sin DATABASE_URL → archivos locales: "
                "estado_tareo.pkl (DataFrame), usuarios.json (hashes SHA-256), "
                "config.json (reglas). Ideal para desarrollo local o trabajo sin conexión. "
                "Mismo código, cero configuración adicional.", "normal")],
        ], colWidths=[half - 0.4 * cm], style=TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), GRIS_CL),
            ("BOX",           (0,0), (-1,-1), 0.8, BORDE),
            ("TOPPADDING",    (0,0), (-1,-1), 10),
            ("BOTTOMPADDING", (0,0), (-1,-1), 10),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ])),
    ]]
    story.append(Table(dual_data, colWidths=[half, half], style=TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1),  6),
        ("RIGHTPADDING", (1,0),(1,-1),  0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ])))

    # ════════════════════════════════════════════════════════════════════════
    # PÁGINA 4 — DB SCHEMA + SEGURIDAD + CONCURRENCIA + RENDER
    # ════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Spacer(1, 0.3 * cm))

    # Esquema DB
    story.append(SeccionTitulo("Esquema de Base de Datos — Supabase / PostgreSQL 17.6", "🗄", cw))
    story.append(Spacer(1, 6))

    def _db_cell(titulo, lineas):
        rows = [[_p(titulo, "mono_dk", fontSize=8.5, fontName="Courier-Bold")]]
        for l in lineas:
            rows.append([_p(l, "mono")])
        return Table(rows, colWidths=[cw / 3 - 0.4 * cm], style=TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), DARK_BG),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("BOX",           (0,0), (-1,-1), 0.8, HexColor("#1E293B")),
        ]))

    db_cells = [
        _db_cell("TABLE: usuarios", [
            "usuario  TEXT  PK",
            "salt     TEXT",
            "hash     TEXT  -- SHA-256",
            "rol      TEXT  -- coord/sup",
            "grupo    TEXT  -- NULL coord",
        ]),
        _db_cell("TABLE: config", [
            "id    INT PK = 1",
            "data  JSONB",
            "  -- refrigerio_min",
            "  -- grupos_sin_refrig",
            "  -- jornadas, producto",
        ]),
        _db_cell("TABLE: tareo", [
            "id        SERIAL PK",
            "NOMBRES   TEXT",
            "GRUPO     TEXT",
            "Corrido   BOOL",
            "Aprobado  BOOL",
            "... +15 columnas",
        ]),
    ]
    third = cw / 3
    story.append(Table([db_cells], colWidths=[third, third, third], style=TableStyle([
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(1,-1),  5),
        ("RIGHTPADDING", (2,0),(2,-1),  0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ])))
    story.append(Spacer(1, 8))

    db_notes = [
        ["Tabla",   "Estrategia de escritura"],
        ["usuarios","Upsert (INSERT … ON CONFLICT DO UPDATE) — idempotente"],
        ["config",  "Upsert sobre id=1 — fila única global editable desde el sidebar"],
        ["tareo",   "TRUNCATE + INSERT al cargar · UPDATE WHERE id IN (grupo) al editar supervisor"],
    ]
    story.append(_tabla(db_notes, [2.5 * cm, cw - 2.5 * cm], hdr_color=AZUL_BG))
    story.append(Spacer(1, 0.35 * cm))

    # Seguridad
    story.append(SeccionTitulo("Seguridad del Aplicativo", "🔒", cw))
    story.append(Spacer(1, 6))

    seg_data = [
        ["✔", "Elemento", "Implementación"],
        ["🔐", "Contraseñas", "Hash SHA-256 con sal aleatoria de 16 chars hex. Nunca almacenadas en claro en DB ni logs"],
        ["🌐", "Conexión SSL", "sslmode=require en la cadena de conexión Supabase. Cifrado en tránsito garantizado"],
        ["🚫", ".env en .gitignore", "Creado y verificado (git check-ignore .env) ANTES del primer commit del repositorio"],
        ["🔑", "Secretos en Render", "DATABASE_URL definida solo en Render Environment (sync: false en render.yaml)"],
        ["👤", "Control de roles", "Middleware en app.py: supervisores solo ven/editan su grupo — filtro por GRUPO_USER"],
        ["📄", ".env.example", "Documenta variables necesarias con valores de ejemplo, nunca credenciales reales"],
        ["🛡️", "NullPool SQLAlchemy", "Previene conexiones persistentes que causarían errores en entorno serverless Render"],
    ]
    story.append(_tabla(seg_data, [0.5 * cm, 2.8 * cm, cw - 3.3 * cm],
        style_extra=[("FONTSIZE", (0,1), (0,-1), 10)],
        hdr_color=ROJO_CL))
    story.append(Spacer(1, 0.35 * cm))

    # Concurrencia multi-supervisor
    story.append(SeccionTitulo("Concurrencia Multi-Supervisor — Sin conflictos", "⚡", cw))
    story.append(Spacer(1, 6))

    conc_data = [
        ["Actor", "Operación DB", "Alcance", "Conflicto"],
        ["Coordinador\n(carga inicial)", "TRUNCATE tareo\nINSERT INTO tareo", "Todos los grupos", "No — operación inicial única"],
        ["Supervisor Gr. N\n(edita condiciones)", "UPDATE tareo\nWHERE id IN (filas_N)", "Solo grupo N", "No — no toca otros grupos"],
        ["Supervisor Gr. E\n(edita condiciones)", "UPDATE tareo\nWHERE id IN (filas_E)", "Solo grupo E", "No — no toca otros grupos"],
        ["Supervisor Gr. 1…5\n(aprueba)", "UPDATE tareo SET\nAprobado=TRUE WHERE...", "Solo su grupo", "No — UPDATE atómico por grupo"],
        ["Coordinador\n(reporte final)", "SELECT * FROM tareo\nWHERE Aprobado=TRUE", "Todos los grupos", "No — solo lectura"],
    ]
    story.append(_tabla(conc_data,
        [2.8 * cm, 3.4 * cm, 2.6 * cm, cw - 8.8 * cm],
        hdr_color=VERDE_CL,
        style_extra=[
            ("FONTSIZE", (0,1), (-1,-1), 7.2),
            ("LEADING",  (0,1), (-1,-1), 10),
        ]))
    story.append(Spacer(1, 0.35 * cm))

    # Despliegue Render
    story.append(SeccionTitulo("Despliegue en Render — Producción", "☁", cw))
    story.append(Spacer(1, 6))

    render_data = [
        ["Parámetro", "Valor"],
        ["URL pública",      "https://operaciones-ysvc.onrender.com"],
        ["Blueprint",        "render.yaml (en repositorio) — gestiona build + start + env"],
        ["Rama seguida",     "main (auto-deploy en cada push)"],
        ["Runtime",          "Python 3.12.7 (.python-version)"],
        ["Build command",    "pip install -r requirements.txt"],
        ["Start command",    "streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true"],
        ["DATABASE_URL",     "Variable secreta en Render Environment (sync: false — nunca en repo)"],
        ["Plan",             "Free (1 instancia web, sleep por inactividad > 15 min)"],
    ]
    story.append(_tabla(render_data, [3.0 * cm, cw - 3.0 * cm], hdr_color=AZUL_BG))

    # ════════════════════════════════════════════════════════════════════════
    # PÁGINA 5 — DASHBOARD GRÁFICOS + WHATSAPP + ARCHIVOS
    # ════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Spacer(1, 0.3 * cm))

    # Dashboard gráficos
    story.append(SeccionTitulo("Dashboard — 7 Gráficos Interactivos (Plotly)", "📊", cw))
    story.append(Spacer(1, 6))

    graf_data = [
        ["#", "Gráfico", "Tipo", "Datos mostrados"],
        ["A1", "Distribución de Turnos",         "Donut",          "% DÍA vs NOCHE · etiquetas con conteo y porcentaje"],
        ["A2", "Personas por Grupo y Turno",      "Barras apiladas","Conteo DÍA+NOCHE por cada grupo de trabajo"],
        ["A3", "Condiciones de Jornada",          "Pie",            "Normal / Corrido (C) / Teórico 12h · % de cada uno"],
        ["A4", "Prom. Horas Marcación por Grupo", "Barras horiz.",  "Promedio de horas brutas por grupo · escala de color"],
        ["B1", "TTHH Desglosado por Grupo",       "Barras apiladas","Hora normal + hora 25% + hora 35% acumulado"],
        ["B2", "Distribución Total Horas Extra",  "Donut",          "% Normal vs 25% vs 35% sobre el total de TTHH"],
        ["B3", "Estado de Aprobación por Grupo",  "Barras horiz.",  "Aprobados (verde) vs Pendientes (gris) por grupo"],
    ]
    story.append(_tabla(graf_data,
        [0.6 * cm, 4.5 * cm, 2.6 * cm, cw - 7.7 * cm],
        style_extra=[
            ("BACKGROUND", (0, 1), (0, 4), AZUL_BG),
            ("BACKGROUND", (0, 5), (0, 7), VERDE_CL),
            ("FONTNAME",   (0, 1), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR",  (0, 1), (0, 4), AZUL),
            ("TEXTCOLOR",  (0, 5), (0, 7), VERDE),
        ],
        hdr_color=AZUL_BG))
    story.append(Spacer(1, 6))

    filtros = Table([[
        _p("🔍  Filtros interactivos: ", "titulo"),
        _p("Multiselect grupos (coordinador ve todos, supervisor solo el suyo)  ·  "
           "Turno: DÍA / NOCHE / Todos  ·  KPIs: Registros · TTHH Total · Hora 25% · Hora 35% · % Aprobado", "normal"),
    ]], colWidths=[3.2 * cm, cw - 3.2 * cm], style=TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), AZUL_BG),
        ("BOX",           (0,0), (-1,-1), 0.8, AZUL_CL),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(filtros)
    story.append(Spacer(1, 0.35 * cm))

    # WhatsApp
    story.append(SeccionTitulo("Módulo Compartir por WhatsApp", "📱", cw))
    story.append(Spacer(1, 6))

    wa_data = [
        ["Tipo de mensaje", "Contenido", "Roles", "Método"],
        ["Resumen del Tareo",
         "Total registros · Turnos DÍA/NOCHE · Corrido/Teórico · TTHH total · "
         "Hora 25% y 35% · Detalle por grupo",
         "Todos", "Botón verde → wa.me URL"],
        ["Reporte Operaciones",
         "Total aprobados · Horas por tramo · Detalle por área/grupo con TTHH, "
         "Normal, 25%, 35%",
         "Coord.", "Botón verde → wa.me URL"],
        ["Archivos Excel adjuntos",
         "REPORTE_TAREO_SISTEMA.xlsx (tareo trabajado) · REPORTE_OPERACIONES.xlsx (final)",
         "Todos / Coord.", "Descarga → adjuntar en WhatsApp"],
        ["Gráficos PNG",
         "Cualquier gráfico del Dashboard exportable con el ícono 📷 de la barra "
         "de herramientas de Plotly (escala 2× para alta resolución)",
         "Todos", "Botón 📷 en Plotly → PNG"],
    ]
    story.append(_tabla(wa_data,
        [3.2 * cm, cw - 8.5 * cm, 1.6 * cm, 3.1 * cm],
        hdr_color=VERDE_CL,
        style_extra=[
            ("BACKGROUND", (0,1), (0,1), VERDE_CL),
            ("BACKGROUND", (0,2), (0,2), AZUL_BG),
            ("BACKGROUND", (0,3), (0,3), AMBAR_CL),
            ("BACKGROUND", (0,4), (0,4), TEAL_CL),
        ]))
    story.append(Spacer(1, 0.35 * cm))

    # Archivos del proyecto
    story.append(SeccionTitulo("Archivos del Proyecto", "📁", cw))
    story.append(Spacer(1, 6))

    arch_data = [
        ["Archivo", "Líneas", "Descripción"],
        ["app.py",                           "~780", "Dashboard Streamlit — 6 pestañas, login, sidebar, estado"],
        ["tareo_core.py",                    "~567", "Motor RR.HH. — cálculo TTHH, tramos, exportar Excel/CSV"],
        ["dashboard_charts.py",              "~230", "7 gráficos Plotly + helpers texto/URL WhatsApp"],
        ["db.py",                            "~270", "Capa Supabase — engine, init_schema, CRUD tareo/config/usuarios"],
        ["auth.py",                          "~145", "Autenticación SHA-256 + salt, crear/actualizar/eliminar usuarios"],
        ["generar_requerimiento_murdoch.py", "~516", "Generador PDF requerimiento integración Murdoch Sistemas"],
        ["render.yaml",                      "16",   "Blueprint Render — tipo web, build/start, envVars"],
        ["requirements.txt",                 "7",    "streamlit · pandas · plotly · openpyxl · SQLAlchemy · psycopg2"],
        [".env.example",                     "6",    "Template DATABASE_URL sin valores reales (seguridad)"],
        ["REPORTE_TAREO_SISTEMA.xlsx",       "—",    "Archivo de ejemplo — 160 registros de asistencia"],
        ["REPORTE_OPERACIONES.xlsx",         "—",    "Archivo de referencia — reporte corporativo validado"],
    ]
    story.append(_tabla(arch_data,
        [5.0 * cm, 1.4 * cm, cw - 6.4 * cm],
        style_extra=[
            ("FONTNAME", (0, 1), (0, -1), "Courier"),
            ("TEXTCOLOR",(0, 1), (0, -1), AZUL),
            ("BACKGROUND",(0,8),(2,8), ROJO_CL),
        ],
        hdr_color=AZUL_BG))

    # Fecha generación
    story.append(Spacer(1, 0.5 * cm))
    story.append(Table([[
        _p(f"Generado: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  "
           f"Versión: main · commit a8cbd74",
           "footer")
    ]], colWidths=[cw], style=TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ])))

    # ─── BUILD ──────────────────────────────────────────────────────────────
    doc.build(story)

    with open(output_path, "wb") as f:
        f.write(buf.getvalue())
    print(f"PDF generado: {output_path}  ({len(buf.getvalue())//1024} KB)")


if __name__ == "__main__":
    build_pdf("infografia_pecepe.pdf")
