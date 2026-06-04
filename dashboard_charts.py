"""
dashboard_charts.py
===================
Gráficos Plotly y helpers de WhatsApp para el Dashboard del Tareo PECEPE.
"""
import calendar as _cal
import datetime as _dt
import urllib.parse

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Paleta corporativa PECEPE
_C = {
    "azul":     "#1F4E9B",
    "dia":      "#F59E0B",
    "noche":    "#1E3A8A",
    "normal":   "#10B981",
    "h25":      "#F59E0B",
    "h35":      "#EF4444",
    "corrido":  "#8B5CF6",
    "teorico":  "#06B6D4",
    "aprobado": "#10B981",
    "pendiente":"#D1D5DB",
}
_TEMPLATE = "plotly_white"
_MARGIN   = dict(t=50, b=35, l=40, r=15)
_PNG_CFG  = {"toImageButtonOptions": {"format": "png", "filename": "pecepe_grafico", "scale": 2}}


def _layout(fig, title="", h=330):
    fig.update_layout(
        template=_TEMPLATE, height=h, margin=_MARGIN,
        title=dict(text=title, font=dict(size=13, color=_C["azul"])),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
    )
    return fig


# --------------------------------------------------------------------------- #
#  Gráficos — Sección A: Tareo Original                                        #
# --------------------------------------------------------------------------- #

def graf_turnos(df: pd.DataFrame) -> go.Figure:
    """Donut: distribución DÍA / NOCHE."""
    cnt = df["TURNO"].value_counts().reset_index()
    cnt.columns = ["Turno", "Personas"]
    colors = [_C["dia"] if t == "DIA" else _C["noche"] for t in cnt["Turno"]]
    fig = px.pie(cnt, names="Turno", values="Personas", hole=0.5,
                 color_discrete_sequence=colors)
    fig.update_traces(textposition="inside", textinfo="percent+label+value",
                      textfont_size=12, pull=[0.03] * len(cnt))
    return _layout(fig, "🌗 Distribución de Turnos")


def graf_registros_grupo(df: pd.DataFrame) -> go.Figure:
    """Barras apiladas: personas por grupo y turno."""
    cnt = df.groupby(["GRUPO", "TURNO"]).size().reset_index(name="Personas")
    fig = px.bar(cnt, x="GRUPO", y="Personas", color="TURNO", barmode="stack",
                 text="Personas",
                 color_discrete_map={"DIA": _C["dia"], "NOCHE": _C["noche"]},
                 labels={"GRUPO": "Grupo", "Personas": "Personas"})
    fig.update_traces(textposition="inside", textfont_size=11)
    fig.update_layout(
        xaxis_title="Grupo", yaxis_title="Personas",
        legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center"),
    )
    return _layout(fig, "👷 Personas por Grupo y Turno")


def graf_condiciones(df: pd.DataFrame) -> go.Figure:
    """Pie: Normal / Corrido / Teórico 12h."""
    corrido = int(df["Corrido"].sum()) if "Corrido" in df.columns else 0
    teorico = int(df["Teorico12"].sum()) if "Teorico12" in df.columns else 0
    normal  = len(df) - corrido - teorico
    fig = px.pie(
        names=["Normal", "Corrido (C)", "Teórico 12h"],
        values=[normal, corrido, teorico],
        color_discrete_sequence=[_C["normal"], _C["corrido"], _C["teorico"]],
        hole=0.45,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label+value",
                      textfont_size=11, pull=[0.02, 0.04, 0.04])
    return _layout(fig, "📋 Condiciones de Jornada")


def graf_horas_marc_grupo(df: pd.DataFrame) -> go.Figure:
    """Barras horizontales: promedio horas de marcación por grupo."""
    agg = (df.groupby("GRUPO")["HORAS_MARCACION"].mean()
             .reset_index().rename(columns={"HORAS_MARCACION": "Horas"}))
    agg = agg.sort_values("Horas")
    agg["etiqueta"] = agg["Horas"].map(lambda x: f"{x:.1f} h")
    fig = px.bar(agg, y="GRUPO", x="Horas", orientation="h",
                 color="Horas",
                 color_continuous_scale=["#DBEAFE", _C["azul"]],
                 text="etiqueta",
                 labels={"GRUPO": "Grupo", "Horas": "Horas promedio"})
    fig.update_traces(textposition="outside", textfont_size=11)
    fig.update_layout(coloraxis_showscale=False, xaxis_title="Horas promedio")
    return _layout(fig, "⏱️ Prom. Horas Marcación por Grupo")


# --------------------------------------------------------------------------- #
#  Gráficos — Sección B: Tareo Final                                           #
# --------------------------------------------------------------------------- #

def graf_tthh_grupo(df: pd.DataFrame) -> go.Figure:
    """Barras apiladas: hora normal + 25% + 35% por grupo."""
    agg = df.groupby("GRUPO").agg(
        Normal=("hora normal", "sum"),
        Hora25=("hora 25", "sum"),
        Hora35=("hora 35", "sum"),
    ).reset_index()
    agg = agg.sort_values("Normal", ascending=False)

    def _lbl(s): return s.map(lambda x: f"{x:.1f}" if x > 0 else "")

    fig = go.Figure([
        go.Bar(name="Hora Normal", x=agg["GRUPO"], y=agg["Normal"],
               marker_color=_C["normal"], text=_lbl(agg["Normal"]),
               textposition="inside", textfont_size=11),
        go.Bar(name="Hora 25%",   x=agg["GRUPO"], y=agg["Hora25"],
               marker_color=_C["h25"],   text=_lbl(agg["Hora25"]),
               textposition="inside", textfont_size=11),
        go.Bar(name="Hora 35%",   x=agg["GRUPO"], y=agg["Hora35"],
               marker_color=_C["h35"],   text=_lbl(agg["Hora35"]),
               textposition="inside", textfont_size=11),
    ])
    fig.update_layout(
        barmode="stack", xaxis_title="Grupo", yaxis_title="Horas",
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
    )
    return _layout(fig, "📊 TTHH Desglosado por Grupo (Normal · 25% · 35%)", h=370)


def graf_dist_horas(df: pd.DataFrame) -> go.Figure:
    """Donut: distribución total hora normal / 25% / 35%."""
    hn  = df["hora normal"].sum() if "hora normal" in df.columns else 0
    h25 = df["hora 25"].sum()     if "hora 25"     in df.columns else 0
    h35 = df["hora 35"].sum()     if "hora 35"     in df.columns else 0
    fig = px.pie(
        names=["Hora Normal", "Hora 25%", "Hora 35%"],
        values=[hn, h25, h35],
        color_discrete_sequence=[_C["normal"], _C["h25"], _C["h35"]],
        hole=0.5,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label+value",
                      textfont_size=11, pull=[0.02, 0.04, 0.04])
    return _layout(fig, "📈 Distribución Total de Horas Extra")


def graf_aprobacion(df: pd.DataFrame) -> go.Figure:
    """Barras horizontales apiladas: aprobados vs pendientes por grupo."""
    agg = df.groupby("GRUPO")["Aprobado"].agg(
        Aprobados=lambda x: int(x.sum()),
        Total="count",
    ).reset_index()
    agg["Pendientes"] = agg["Total"] - agg["Aprobados"]
    agg = agg.sort_values("Total")
    fig = go.Figure([
        go.Bar(name="Aprobados",  y=agg["GRUPO"], x=agg["Aprobados"],
               orientation="h", marker_color=_C["aprobado"],
               text=agg["Aprobados"], textposition="inside", textfont_size=11),
        go.Bar(name="Pendientes", y=agg["GRUPO"], x=agg["Pendientes"],
               orientation="h", marker_color=_C["pendiente"],
               text=agg["Pendientes"], textposition="inside", textfont_size=11),
    ])
    fig.update_layout(
        barmode="stack", xaxis_title="Personas",
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
    )
    return _layout(fig, "✅ Estado de Aprobación por Grupo")


# --------------------------------------------------------------------------- #
#  Textos para WhatsApp                                                        #
# --------------------------------------------------------------------------- #

def _sep():
    return "──────────────────"


def texto_resumen(df: pd.DataFrame, titulo: str = "TAREO") -> str:
    """Genera un resumen formateado para compartir por WhatsApp."""
    total  = len(df)
    dia    = int((df["TURNO"] == "DIA").sum())   if "TURNO"    in df.columns else 0
    noche  = int((df["TURNO"] == "NOCHE").sum()) if "TURNO"    in df.columns else 0
    corrido= int(df["Corrido"].sum())             if "Corrido"  in df.columns else 0
    teorico= int(df["Teorico12"].sum())           if "Teorico12" in df.columns else 0
    tthh   = df["TTHH"].sum()       if "TTHH"        in df.columns else 0
    h_nor  = df["hora normal"].sum() if "hora normal" in df.columns else 0
    h25    = df["hora 25"].sum()     if "hora 25"     in df.columns else 0
    h35    = df["hora 35"].sum()     if "hora 35"     in df.columns else 0
    apro   = int(df["Aprobado"].sum()) if "Aprobado" in df.columns else 0
    pct    = f"{apro/total*100:.0f}%" if total > 0 else "0%"
    fecha  = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")

    lineas = [
        f"🏭 *PECEPE — {titulo}*",
        f"📅 {fecha}",
        _sep(),
        f"👥 *Total registros:* {total}",
        f"☀️ Turno DÍA: {dia}   |   🌙 NOCHE: {noche}",
        f"📋 Corrido: {corrido}   |   ⏱️ Teórico 12h: {teorico}",
        _sep(),
        f"⏱️ *TTHH Total:* {tthh:,.2f} h",
        f"✅ Hora Normal: {h_nor:,.2f} h",
        f"📈 Hora 25%: {h25:,.2f} h",
        f"📈 Hora 35%: {h35:,.2f} h",
        f"✔️ Aprobados: {apro}/{total} ({pct})",
        _sep(),
    ]

    if "GRUPO" in df.columns and "TTHH" in df.columns:
        lineas.append("📋 *Detalle por Grupo:*")
        agg = df.groupby("GRUPO").agg(
            n=("NOMBRES", "count"),
            tt=("TTHH", "sum"),
            v25=("hora 25", "sum"),
            v35=("hora 35", "sum"),
        ).reset_index()
        for _, r in agg.iterrows():
            lineas.append(
                f"  • Gr. {r['GRUPO']}: {int(r['n'])} pers | "
                f"{r['tt']:.1f}h TTHH | 25%: {r['v25']:.1f}h | 35%: {r['v35']:.1f}h"
            )
        lineas.append(_sep())

    lineas.append("🔗 _App Tareo PECEPE_")
    return "\n".join(lineas)


def texto_reporte_final(df_rep: pd.DataFrame) -> str:
    """Genera el texto del reporte de operaciones para WhatsApp."""
    total = len(df_rep)
    horas = df_rep["horas total"].sum() if "horas total" in df_rep.columns else 0
    h_nor = df_rep["hora normal"].sum() if "hora normal" in df_rep.columns else 0
    h25   = df_rep["hora 25"].sum()     if "hora 25"     in df_rep.columns else 0
    h35   = df_rep["hora 35"].sum()     if "hora 35"     in df_rep.columns else 0
    fecha = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")

    lineas = [
        "🏭 *PECEPE — REPORTE OPERACIONES FINAL*",
        f"📅 {fecha}",
        _sep(),
        f"👥 *Total:* {total} registros",
        f"⏱️ *Horas Total:* {horas:,.2f} h",
        f"✅ Hora Normal: {h_nor:,.2f} h",
        f"📈 Hora 25%: {h25:,.2f} h",
        f"📈 Hora 35%: {h35:,.2f} h",
        _sep(),
    ]

    if "AREA" in df_rep.columns:
        lineas.append("📋 *Por Área (Grupo):*")
        agg = df_rep.groupby("AREA").agg(
            n=("NOMBRES",     "count"),
            tot=("horas total","sum"),
            nor=("hora normal","sum"),
            v25=("hora 25",   "sum"),
            v35=("hora 35",   "sum"),
        ).reset_index()
        for _, r in agg.iterrows():
            lineas.append(
                f"  • Área {r['AREA']}: {int(r['n'])} pers | "
                f"Tot {r['tot']:.1f}h | Nor {r['nor']:.1f}h | "
                f"25% {r['v25']:.1f}h | 35% {r['v35']:.1f}h"
            )
        lineas.append(_sep())

    lineas.append("🔗 _App Tareo PECEPE_")
    return "\n".join(lineas)


# --------------------------------------------------------------------------- #
#  Helpers de fecha / semana ISO                                               #
# --------------------------------------------------------------------------- #

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def semanas_del_mes(año: int, mes: int) -> list:
    """Semanas ISO (lun–dom) que tienen al menos un día en el mes dado."""
    primer = _dt.date(año, mes, 1)
    ultimo = _dt.date(año, mes, _cal.monthrange(año, mes)[1])
    semanas, seen = [], set()
    d = primer
    while d <= ultimo:
        iso_year, iso_week, _ = d.isocalendar()
        clave = (iso_year, iso_week)
        if clave not in seen:
            seen.add(clave)
            lun = d - _dt.timedelta(days=d.weekday())
            dom = lun + _dt.timedelta(days=6)
            semanas.append({
                "iso_year": iso_year,
                "num":      iso_week,
                "label":    f"S{iso_week:02d} ({lun.strftime('%d/%m')}–{dom.strftime('%d/%m')})",
                "lunes":    lun,
                "domingo":  dom,
                "dias": [
                    {
                        "nombre": DIAS_ES[i],
                        "fecha":  lun + _dt.timedelta(days=i),
                        "en_mes": (lun + _dt.timedelta(days=i)).month == mes,
                    }
                    for i in range(7)
                ],
            })
        d += _dt.timedelta(days=1)
    return semanas


def agregar_cols_fecha(df: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas _AÑO, _MES_NUM, _MES_NOMBRE, _SEMANA_NUM, _SEMANA_LABEL."""
    df = df.copy()
    fechas = pd.to_datetime(df["FECHA"], errors="coerce")
    iso = fechas.dt.isocalendar()
    df["_AÑO"]        = iso["year"].astype("Int64")
    df["_MES_NUM"]    = fechas.dt.month.astype("Int64")
    df["_MES_NOMBRE"] = df["_MES_NUM"].map(MESES_ES).fillna("")
    df["_SEMANA_NUM"] = iso["week"].astype("Int64")

    def _lbl(d):
        if pd.isna(d):
            return ""
        lun = d - pd.Timedelta(days=d.weekday())
        dom = lun + pd.Timedelta(days=6)
        w = d.isocalendar()[1]
        return f"S{w:02d} ({lun.strftime('%d/%m')}–{dom.strftime('%d/%m')})"

    df["_SEMANA_LABEL"] = fechas.apply(_lbl)
    return df


def graf_registros_semana(df: pd.DataFrame) -> go.Figure:
    """Barras apiladas: registros DÍA/NOCHE por semana ISO."""
    df2 = agregar_cols_fecha(df)
    df2 = df2.dropna(subset=["_SEMANA_NUM"])
    cnt = (df2.groupby(["_SEMANA_LABEL", "_SEMANA_NUM", "TURNO"])
              .size().reset_index(name="Registros"))
    cnt = cnt.sort_values("_SEMANA_NUM")
    fig = px.bar(
        cnt, x="_SEMANA_LABEL", y="Registros", color="TURNO",
        barmode="stack", text="Registros",
        color_discrete_map={"DIA": _C["dia"], "NOCHE": _C["noche"]},
        labels={"_SEMANA_LABEL": "Semana", "Registros": "Personas"},
    )
    fig.update_traces(textposition="inside", textfont_size=11)
    fig.update_layout(
        xaxis_title="Semana ISO", yaxis_title="Personas",
        legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center"),
    )
    return _layout(fig, "📅 Registros por Semana del Año (DÍA · NOCHE)", h=350)


def graf_tthh_semana(df: pd.DataFrame) -> go.Figure:
    """Barras apiladas: Hora Normal + 25% + 35% por semana ISO."""
    df2 = agregar_cols_fecha(df)
    df2 = df2.dropna(subset=["_SEMANA_NUM"])
    agg = (df2.groupby(["_SEMANA_LABEL", "_SEMANA_NUM"]).agg(
        Normal=("hora normal", "sum"),
        Hora25=("hora 25",    "sum"),
        Hora35=("hora 35",    "sum"),
    ).reset_index().sort_values("_SEMANA_NUM"))

    def _lbl(s): return s.map(lambda x: f"{x:.1f}" if x > 0 else "")

    fig = go.Figure([
        go.Bar(name="Hora Normal", x=agg["_SEMANA_LABEL"], y=agg["Normal"],
               marker_color=_C["normal"], text=_lbl(agg["Normal"]),
               textposition="inside", textfont_size=10),
        go.Bar(name="Hora 25%",   x=agg["_SEMANA_LABEL"], y=agg["Hora25"],
               marker_color=_C["h25"],   text=_lbl(agg["Hora25"]),
               textposition="inside", textfont_size=10),
        go.Bar(name="Hora 35%",   x=agg["_SEMANA_LABEL"], y=agg["Hora35"],
               marker_color=_C["h35"],   text=_lbl(agg["Hora35"]),
               textposition="inside", textfont_size=10),
    ])
    fig.update_layout(
        barmode="stack", xaxis_title="Semana ISO", yaxis_title="Horas",
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
    )
    return _layout(fig, "📊 TTHH por Semana del Año (Normal · 25% · 35%)", h=370)


def generar_pdf_resumen(df: pd.DataFrame, titulo: str = "TAREO PECEPE") -> bytes:
    """Genera un PDF resumido del tareo o reporte (para descargar y compartir)."""
    from io import BytesIO
    from reportlab.lib import colors as rc
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    sty = getSampleStyleSheet()
    azul = rc.HexColor("#1F4E9B")

    h1 = ParagraphStyle("H1", parent=sty["Heading1"], textColor=azul,
                         fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=sty["Heading2"], textColor=azul,
                         fontSize=13, spaceAfter=6, spaceBefore=14)
    ft = ParagraphStyle("FT", parent=sty["Normal"], textColor=rc.grey,
                         fontSize=8, alignment=1)

    # Detecta si es tareo o reporte final por nombres de columnas
    col_horas  = "horas total" if "horas total" in df.columns else "TTHH"
    col_grupo  = "AREA"        if "AREA"        in df.columns else "GRUPO"
    col_nombre = "NOMBRES"     if "NOMBRES"     in df.columns else None

    total = len(df)
    dia   = int((df["TURNO"] == "DIA").sum())   if "TURNO"    in df.columns else 0
    noche = int((df["TURNO"] == "NOCHE").sum()) if "TURNO"    in df.columns else 0
    tthh  = float(df[col_horas].sum())          if col_horas  in df.columns else 0.0
    h25   = float(df["hora 25"].sum())          if "hora 25"  in df.columns else 0.0
    h35   = float(df["hora 35"].sum())          if "hora 35"  in df.columns else 0.0
    apro  = int(df["Aprobado"].sum())           if "Aprobado" in df.columns else 0

    _bg   = [rc.HexColor("#EEF2FF"), rc.white]
    _grid = rc.HexColor("#C7D2E8")

    def _tbl(data, widths):
        t = Table(data, colWidths=widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1,  0),  azul),
            ("TEXTCOLOR",      (0, 0), (-1,  0),  rc.white),
            ("FONTNAME",       (0, 0), (-1,  0),  "Helvetica-Bold"),
            ("FONTNAME",       (0, 1), ( 0, -1),  "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1),  11),
            ("ALIGN",          (1, 0), (-1, -1),  "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),  _bg),
            ("GRID",           (0, 0), (-1, -1),  0.5, _grid),
            ("TOPPADDING",     (0, 0), (-1, -1),  7),
            ("BOTTOMPADDING",  (0, 0), (-1, -1),  7),
        ]))
        return t

    story = [
        Paragraph("PECEPE – Tareo de Operaciones", h1),
        Paragraph(titulo, sty["Heading2"]),
        Paragraph(f"Generado: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}",
                  sty["Normal"]),
        Spacer(1, 0.5 * cm),
        _tbl([
            ["Indicador",     "Valor"],
            ["Total Registros", str(total)],
            ["Turno DIA",       str(dia)],
            ["Turno NOCHE",     str(noche)],
            ["Horas Total",     f"{tthh:.2f} h"],
            ["Hora 25%",        f"{h25:.2f} h"],
            ["Hora 35%",        f"{h35:.2f} h"],
            ["Aprobados",       f"{apro} / {total}"],
        ], [9 * cm, 6 * cm]),
    ]

    if col_grupo in df.columns and col_horas in df.columns and total > 0:
        story.append(Paragraph("Detalle por Grupo", h2))
        cnt_col = col_nombre if col_nombre and col_nombre in df.columns else col_horas
        agg = df.groupby(col_grupo).agg(n=(cnt_col, "count"),
                                         hh=(col_horas, "sum")).reset_index()
        if "hora 25" in df.columns:
            agg = agg.join(df.groupby(col_grupo)["hora 25"].sum().rename("v25"),
                           on=col_grupo)
        else:
            agg["v25"] = 0.0
        if "hora 35" in df.columns:
            agg = agg.join(df.groupby(col_grupo)["hora 35"].sum().rename("v35"),
                           on=col_grupo)
        else:
            agg["v35"] = 0.0

        gdata = [["Grupo", "Personas", "Horas (h)", "Hora 25%", "Hora 35%"]]
        for _, r in agg.iterrows():
            gdata.append([str(r[col_grupo]), str(int(r["n"])),
                          f"{r['hh']:.1f}", f"{r['v25']:.1f}", f"{r['v35']:.1f}"])
        gt = Table(gdata, colWidths=[3 * cm, 3 * cm, 3.5 * cm, 3.5 * cm, 3 * cm])
        gt.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1,  0),  azul),
            ("TEXTCOLOR",      (0, 0), (-1,  0),  rc.white),
            ("FONTNAME",       (0, 0), (-1,  0),  "Helvetica-Bold"),
            ("FONTSIZE",       (0, 0), (-1, -1),  10),
            ("ALIGN",          (1, 0), (-1, -1),  "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),  _bg),
            ("GRID",           (0, 0), (-1, -1),  0.5, _grid),
            ("TOPPADDING",     (0, 0), (-1, -1),  6),
            ("BOTTOMPADDING",  (0, 0), (-1, -1),  6),
        ]))
        story.append(gt)

    story += [Spacer(1, 1 * cm),
              Paragraph("PECEPE – App Tareo de Operaciones – DONET 2026", ft)]
    doc.build(story)
    return buf.getvalue()


def url_wa(texto: str) -> str:
    """Genera la URL de WhatsApp Web con el texto codificado."""
    return f"https://wa.me/?text={urllib.parse.quote(texto)}"


def boton_wa_html(url: str, etiqueta: str = "💬 Abrir WhatsApp") -> str:
    """Devuelve el HTML del botón verde de WhatsApp."""
    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
        f'<button style="background:#25D366;color:#fff;border:none;'
        f'padding:10px 22px;border-radius:8px;cursor:pointer;'
        f'font-size:14px;font-weight:600;margin-top:6px;">'
        f'{etiqueta}</button></a>'
    )
