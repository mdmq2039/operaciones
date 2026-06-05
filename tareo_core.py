"""
tareo_core.py
=================
Motor de calculo del aplicativo de Tareo de Operaciones (PECEPE).

Convierte el archivo del sistema de asistencia (REPORTE_TAREO_SISTEMA) en el
reporte final (REPORTE_OPERACIONES) aplicando las reglas de negocio de RR.HH.:

  - Horas de marcacion (bruto) = salida - entrada (con cruce de medianoche).
  - Se descuentan 45 min de refrigerio, SALVO que:
        * el grupo este en la lista "sin refrigerio" (E, PCP, N por defecto), o
        * la observacion sea "C" (corrido), o
        * la observacion sea "12" (jornada teorica de 12 h).
  - Observacion "12": TTHH = 12 h exactas y la hora de inicio/salida se vuelven
        teoricas (dia 07:00-19:00, noche 19:00-07:00, configurable).
  - Descuento extra "menos 1/2/3": resta 1, 2 o 3 horas adicionales.
  - TTHH (Total Horas RR.HH.) es la base para el reporte de operaciones.

Las horas extra del reporte final se reparten en tramos:
  - hora normal  : hasta 8 h
  - hora 25      : siguientes 2 h (8 -> 10)
  - hora 35      : lo que exceda de 10 h
  - hora 100     : domingos / feriados (manual)
  - BONO HH      : manual
"""

from __future__ import annotations

import datetime as _dt
import json as _json
import os as _os
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import pandas as pd

# Estado compartido en disco: permite que varios supervisores trabajen el
# MISMO tareo de forma concurrente y que el coordinador vea todo consolidado.
_RUTA_BASE = _os.path.dirname(_os.path.abspath(__file__))
ARCHIVO_ESTADO = _os.path.join(_RUTA_BASE, "estado_tareo.pkl")
ARCHIVO_CONFIG = _os.path.join(_RUTA_BASE, "config.json")


def existe_estado() -> bool:
    return _os.path.exists(ARCHIVO_ESTADO)


def guardar_estado(df: pd.DataFrame) -> None:
    df.to_pickle(ARCHIVO_ESTADO)


def cargar_estado() -> Optional[pd.DataFrame]:
    if not existe_estado():
        return None
    try:
        return pd.read_pickle(ARCHIVO_ESTADO)
    except Exception:
        return None


def borrar_estado() -> None:
    if existe_estado():
        _os.remove(ARCHIVO_ESTADO)


# --------------------------------------------------------------------------- #
#  Configuracion (valores por defecto, editables desde el dashboard)          #
# --------------------------------------------------------------------------- #
@dataclass
class Config:
    refrigerio_min: int = 45                 # minutos de refrigerio
    grupos_sin_refrigerio: tuple = ("E", "PCP", "N", "5")
    # Jornadas teoricas para observacion "12"
    teorico_dia_inicio: str = "07:00"
    teorico_dia_salida: str = "19:00"
    # Dos opciones validas de jornada nocturna (seleccionables masiva/individual)
    jornada_noche_opciones: dict = field(default_factory=lambda: {
        "19:00-07:00": ("19:00", "07:00"),
        "20:00-08:00": ("20:00", "08:00"),
    })
    jornada_noche_default: str = "19:00-07:00"
    horas_teoricas_12: float = 12.0
    # Tramos de horas extra
    tope_normal: float = 8.0
    tope_25: float = 2.0                      # ancho del tramo 25% (8 -> 10)
    # Valores fijos del reporte de operaciones
    producto: str = "POTA"
    zona: Any = 1
    # Texto del horario que identifica el turno noche
    palabra_noche: str = "noche"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["grupos_sin_refrigerio"] = list(self.grupos_sin_refrigerio)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Config":
        d = dict(d or {})
        if "grupos_sin_refrigerio" in d:
            d["grupos_sin_refrigerio"] = tuple(d["grupos_sin_refrigerio"])
        if "jornada_noche_opciones" in d:
            d["jornada_noche_opciones"] = {
                k: tuple(v) for k, v in d["jornada_noche_opciones"].items()
            }
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid})


def guardar_config(cfg: "Config") -> None:
    with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as f:
        _json.dump(cfg.to_dict(), f, ensure_ascii=False, indent=2)


def cargar_config() -> "Config":
    if not _os.path.exists(ARCHIVO_CONFIG):
        return Config()
    try:
        with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
            return Config.from_dict(_json.load(f))
    except Exception:
        return Config()


# --------------------------------------------------------------------------- #
#  Utilidades de tiempo                                                        #
# --------------------------------------------------------------------------- #
def _to_time(value: Any) -> Optional[_dt.time]:
    """Convierte celdas variadas (time, datetime, str, float Excel) a time."""
    if value is None or value == "":
        return None
    if isinstance(value, _dt.time):
        return value
    if isinstance(value, _dt.datetime):
        return value.time()
    if isinstance(value, (int, float)):
        # fraccion de dia estilo Excel
        try:
            total = float(value)
            frac = total - int(total)
            seconds = round(frac * 86400)
            return (_dt.datetime.min + _dt.timedelta(seconds=seconds)).time()
        except Exception:
            return None
    s = str(value).strip()
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p"):
        try:
            return _dt.datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _hours_between(entrada: Optional[_dt.time], salida: Optional[_dt.time]) -> float:
    """Horas decimales entre entrada y salida, manejando cruce de medianoche."""
    if entrada is None or salida is None:
        return 0.0
    base = _dt.datetime(2000, 1, 1, entrada.hour, entrada.minute, entrada.second)
    end = _dt.datetime(2000, 1, 1, salida.hour, salida.minute, salida.second)
    if end <= base:
        end += _dt.timedelta(days=1)
    return (end - base).total_seconds() / 3600.0


def hours_to_hhmm(h: float) -> str:
    """0.h decimal -> 'HH:MM'."""
    if h is None or pd.isna(h):
        return ""
    if h < 0:
        h = 0.0
    total_min = int(round(h * 60))
    return f"{total_min // 60:02d}:{total_min % 60:02d}"


def _time_str(value: Any) -> str:
    t = _to_time(value)
    return t.strftime("%H:%M") if t else ""


def _parse_observacion(raw: Any) -> dict:
    """Interpreta la columna OBSERVADOS del sistema.

    Devuelve flags: corrido, teorico12, descuento_extra (horas).
    """
    out = {"corrido": False, "teorico12": False, "descuento_extra": 0.0, "raw": raw}
    if raw is None:
        return out
    s = str(raw).strip().lower()
    if s in ("", "none", "nan"):
        return out
    if s in ("c", "corrido"):
        out["corrido"] = True
    elif s in ("12", "12.0"):
        out["teorico12"] = True
    elif s.startswith("menos"):
        digits = "".join(ch for ch in s if ch.isdigit())
        out["descuento_extra"] = float(digits) if digits else 0.0
    elif s.isdigit():
        # numero suelto distinto de 12 -> lo tomamos como teorico de 12 si es 12
        if s == "12":
            out["teorico12"] = True
    return out


# --------------------------------------------------------------------------- #
#  Carga del archivo del sistema                                              #
# --------------------------------------------------------------------------- #
COL_ALIASES = {
    "nombre completo": "nombre",
    "nombres": "nombre",
    "id": "id",
    "grupos": "grupo",
    "grupo": "grupo",
    "departamento": "departamento",
    "fecha": "fecha",
    "horario": "horario",
    "hora de fichaje a la entrada": "entrada",
    "hora de fichaje a la salida": "salida",
    "tthh": "tthh_sistema",
    "horas trabajadas": "horas_sistema",
    "observados": "observacion",
    "observacion": "observacion",
    "observaciones": "observacion",
}


def cargar_tareo_sistema(file) -> pd.DataFrame:
    """Lee REPORTE_TAREO_SISTEMA.xlsx detectando la fila de cabecera real."""
    raw = pd.read_excel(file, header=None, dtype=object)
    header_row = None
    for i in range(min(15, len(raw))):
        valores = [str(v).strip().lower() for v in raw.iloc[i].tolist()]
        if "nombre completo" in valores or "nombres" in valores:
            header_row = i
            break
    if header_row is None:
        header_row = 0

    df = pd.read_excel(file, header=header_row, dtype=object)
    df = df.dropna(how="all")
    # Normaliza nombres de columna
    rename = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if key in COL_ALIASES:
            rename[col] = COL_ALIASES[key]
    df = df.rename(columns=rename)
    # Asegura columnas minimas
    for needed in ("nombre", "grupo", "departamento", "fecha", "horario",
                   "entrada", "salida", "observacion"):
        if needed not in df.columns:
            df[needed] = None
    # Filtra filas sin nombre valido
    df = df[df["nombre"].notna()].copy()
    df = df[df["nombre"].astype(str).str.strip() != ""].copy()
    df = df.reset_index(drop=True)
    return df


# --------------------------------------------------------------------------- #
#  Construccion de la tabla de trabajo (editable en el dashboard)             #
# --------------------------------------------------------------------------- #
def construir_tabla_trabajo(df_sistema: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """A partir del crudo del sistema arma la tabla editable con las nuevas
    columnas GRUPO, OBSERVACION y los flags por defecto para llegar a TTHH."""
    filas = []
    for _, r in df_sistema.iterrows():
        entrada = _to_time(r.get("entrada"))
        salida = _to_time(r.get("salida"))
        bruto = _hours_between(entrada, salida)

        horario = str(r.get("horario") or "")
        es_noche = cfg.palabra_noche.lower() in horario.lower()

        grupo = r.get("grupo")
        grupo_str = "" if grupo is None else str(grupo).strip()
        if grupo_str.endswith(".0"):
            grupo_str = grupo_str[:-2]

        obs = _parse_observacion(r.get("observacion"))

        grupo_sin_refri = grupo_str.upper() in {g.upper() for g in cfg.grupos_sin_refrigerio}

        fila = {
            "Aprobado": False,
            "NOMBRES": str(r.get("nombre")).strip(),
            "GRUPO": grupo_str,
            "SERVICE": "" if r.get("departamento") is None else str(r.get("departamento")).strip(),
            "FECHA": r.get("fecha"),
            "TURNO": "NOCHE" if es_noche else "DIA",
            "ENTRADA": entrada.strftime("%H:%M") if entrada else "",
            "SALIDA": salida.strftime("%H:%M") if salida else "",
            "HORAS_MARCACION": round(bruto, 4),
            # Flags de condiciones (editables / chequeables)
            "Corrido": bool(obs["corrido"]),
            "Teorico12": bool(obs["teorico12"]),
            "DescuentoExtra": float(obs["descuento_extra"]),
            "AumentoExtra": 0.0,
            "Refrigerio": not (grupo_sin_refri or obs["corrido"] or obs["teorico12"]),
            "JornadaNoche": cfg.jornada_noche_default,
            "OBSERVACION": "" if r.get("observacion") is None else str(r.get("observacion")).strip(),
        }
        filas.append(fila)
    df = pd.DataFrame(filas)
    return recalcular(df, cfg)


# --------------------------------------------------------------------------- #
#  Recalculo de TTHH y tramos a partir de los flags                           #
# --------------------------------------------------------------------------- #
def _tthh_de_fila(row: pd.Series, cfg: Config) -> float:
    if bool(row.get("Teorico12")):
        return float(cfg.horas_teoricas_12)
    bruto = float(row.get("HORAS_MARCACION") or 0.0)
    descuento = 0.0
    if bool(row.get("Refrigerio")) and not bool(row.get("Corrido")):
        descuento += cfg.refrigerio_min / 60.0
    descuento += float(row.get("DescuentoExtra") or 0.0)
    aumento = float(row.get("AumentoExtra") or 0.0)
    return max(0.0, round(bruto - descuento + aumento, 4))


def _inicio_salida_final(row: pd.Series, cfg: Config) -> tuple[str, str]:
    """INICIO/SALIDA para el reporte: teoricos si es jornada de 12, reales si no."""
    if bool(row.get("Teorico12")):
        if str(row.get("TURNO")).upper() == "NOCHE":
            opcion = str(row.get("JornadaNoche") or cfg.jornada_noche_default)
            ini, sal = cfg.jornada_noche_opciones.get(
                opcion, cfg.jornada_noche_opciones[cfg.jornada_noche_default])
            return ini, sal
        return cfg.teorico_dia_inicio, cfg.teorico_dia_salida
    return str(row.get("ENTRADA") or ""), str(row.get("SALIDA") or "")


def recalcular(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Recalcula TTHH, INICIO/SALIDA finales y tramos de horas para toda la tabla."""
    df = df.copy()
    tthh, inicios, salidas = [], [], []
    h_norm, h25, h35 = [], [], []
    for _, row in df.iterrows():
        t = _tthh_de_fila(row, cfg)
        ini, sal = _inicio_salida_final(row, cfg)
        tthh.append(t)
        inicios.append(ini)
        salidas.append(sal)
        n = min(t, cfg.tope_normal)
        e25 = min(max(t - cfg.tope_normal, 0.0), cfg.tope_25)
        e35 = max(t - cfg.tope_normal - cfg.tope_25, 0.0)
        h_norm.append(round(n, 4))
        h25.append(round(e25, 4))
        h35.append(round(e35, 4))
    df["TTHH"] = tthh
    df["TTHH_HHMM"] = [hours_to_hhmm(x) for x in tthh]
    df["HORAS_MARC_HHMM"] = [hours_to_hhmm(x) for x in df["HORAS_MARCACION"]]
    df["INICIO_FINAL"] = inicios
    df["SALIDA_FINAL"] = salidas
    df["hora normal"] = h_norm
    df["hora 25"] = h25
    df["hora 35"] = h35
    return df


# --------------------------------------------------------------------------- #
#  Acciones masivas (checks)                                                   #
# --------------------------------------------------------------------------- #
def aplicar_masivo(df: pd.DataFrame, columna: str, valor: Any,
                   mask: Optional[pd.Series] = None) -> pd.DataFrame:
    """Aplica un valor a una columna de flags para todas las filas (o un subconjunto)."""
    df = df.copy()
    if mask is None:
        df[columna] = valor
    else:
        df.loc[mask, columna] = valor
    return df


# --------------------------------------------------------------------------- #
#  Nombres de grupos (mapa código → nombre)                                    #
# --------------------------------------------------------------------------- #
NOMBRES_GRUPO = {
    "1": "RECEPCION", "2": "ENVASADO", "3": "ANILLAS",
    "4": "MASA", "5": "EMPAQUE", "N": "NOCHE", "E": "EXTERIOR",
}


def nombre_grupo(g) -> str:
    """Devuelve el nombre legible del grupo; los no mapeados se devuelven igual."""
    return NOMBRES_GRUPO.get(str(g).strip(), str(g).strip())


# --------------------------------------------------------------------------- #
#  Generacion del REPORTE_OPERACIONES                                          #
# --------------------------------------------------------------------------- #
ORDEN_OPERACIONES = [
    "NOMBRES", "PRODUCTO", "TURNO", "ZONA", "AREA", "SERVICE", "FECHA",
    "INICIO", "CORRIDO", "SALIDA", "COMIO", "HORAS TRABAJADAS", "horas total",
    "hora normal", "hora 25", "hora 35", "hora 100", "BONO HH",
]


def generar_reporte_operaciones(df: pd.DataFrame, cfg: Config,
                                solo_aprobados: bool = True) -> pd.DataFrame:
    """Construye el DataFrame final con el orden y nombres del REPORTE_OPERACIONES."""
    df = recalcular(df, cfg)
    if solo_aprobados and "Aprobado" in df.columns:
        df = df[df["Aprobado"] == True].copy()  # noqa: E712

    out = pd.DataFrame()
    out["NOMBRES"] = df["NOMBRES"]
    out["PRODUCTO"] = cfg.producto
    out["TURNO"] = df["TURNO"]
    out["ZONA"] = cfg.zona
    out["AREA"] = df["GRUPO"].map(nombre_grupo)
    out["SERVICE"] = df["SERVICE"]
    out["FECHA"] = df["FECHA"]
    out["INICIO"] = df["INICIO_FINAL"]
    out["CORRIDO"] = df["Corrido"].map(lambda x: "C" if x else None)
    out["SALIDA"] = df["SALIDA_FINAL"]
    out["COMIO"] = df.apply(
        lambda r: None if (r["Refrigerio"] and not r["Corrido"] and not r["Teorico12"]) else "SI",
        axis=1,
    )
    out["HORAS TRABAJADAS"] = df["TTHH"].map(hours_to_hhmm)
    out["horas total"] = df["TTHH"]
    out["hora normal"] = df["hora normal"]
    out["hora 25"] = df["hora 25"]
    out["hora 35"] = df["hora 35"]
    out["hora 100"] = None   # domingos/feriados: manual
    out["BONO HH"] = None    # manual
    return out[ORDEN_OPERACIONES]


# --------------------------------------------------------------------------- #
#  Exportacion a Excel con formato                                            #
# --------------------------------------------------------------------------- #
# Formatos de numero por columna, identicos al archivo REPORTE_OPERACIONES.xlsx
_FORMATOS_OPERACIONES = {
    "FECHA": "mm-dd-yy", "INICIO": "h:mm", "CORRIDO": "h:mm",
    "SALIDA": "h:mm", "COMIO": "h:mm", "HORAS TRABAJADAS": "h:mm",
    "horas total": "0.00", "hora normal": "0.00", "hora 25": "0.00",
    "hora 35": "0.00", "hora 100": "0.00", "BONO HH": "0.00",
}
# Columnas que en el archivo original son valores de HORA reales (datetime.time)
_COLS_HORA_REAL = {"HORAS TRABAJADAS"}


def _hhmm_a_time(valor: Any) -> Optional[_dt.time]:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, _dt.time):
        return valor
    if isinstance(valor, (int, float)):
        total = int(round(float(valor) * 60))
        return _dt.time(min(total // 60, 23), total % 60)
    s = str(valor).strip()
    if not s or ":" not in s:
        return None
    hh, mm = s.split(":")[:2]
    return _dt.time(min(int(hh), 23), int(mm))


def exportar_excel(df_operaciones: pd.DataFrame) -> bytes:
    """Genera el .xlsx replicando el formato exacto de REPORTE_OPERACIONES.xlsx
    (cabecera azul Calibri 8, HORAS TRABAJADAS como hora real, decimales 0.00)."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Hoja1"

    header_fill = PatternFill("solid", fgColor="4472C4")   # azul tema 4
    header_font = Font(name="Calibri", color="FFFFFF", bold=True, size=8)
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    data_align = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    cols = list(df_operaciones.columns)
    ws.append(cols)
    for c, _ in enumerate(cols, start=1):
        cell = ws.cell(row=1, column=c)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = border

    for _, row in df_operaciones.iterrows():
        valores = []
        for col in cols:
            v = row[col]
            if col in _COLS_HORA_REAL:
                v = _hhmm_a_time(v)
            elif isinstance(v, _dt.datetime):
                v = v  # se mantiene como fecha real
            elif isinstance(v, float) and pd.isna(v):
                v = None
            elif v is None or (isinstance(v, str) and v == ""):
                v = None
            valores.append(v)
        ws.append(valores)

    # Aplica formatos de numero y bordes a las celdas de datos
    fmt_por_col = {i + 1: _FORMATOS_OPERACIONES.get(c, "General")
                   for i, c in enumerate(cols)}
    _col_nombres = cols.index("NOMBRES") + 1 if "NOMBRES" in cols else None
    left_align = Alignment(horizontal="left", vertical="center")
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(cols) + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = border
            cell.alignment = left_align if c == _col_nombres else data_align
            cell.number_format = fmt_por_col[c]
            cell.font = Font(name="Calibri", size=8)

    anchos = {
        "NOMBRES": 32, "PRODUCTO": 10, "TURNO": 8, "SERVICE": 12,
        "FECHA": 12, "HORAS TRABAJADAS": 16, "horas total": 11,
    }
    for c, col in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(c)].width = anchos.get(col, 9)

    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# Cabecera del intermedio REPORTE_TAREO_SISTEMA (tareo trabajado por supervisores)
ORDEN_TAREO_TRABAJADO = [
    "NOMBRES", "GRUPO", "SERVICE", "FECHA", "TURNO", "ENTRADA", "SALIDA",
    "HORAS_MARCACION", "Corrido", "Teorico12", "Refrigerio", "DescuentoExtra",
    "JornadaNoche", "OBSERVACION", "TTHH_HHMM", "TTHH", "Aprobado",
]


def exportar_tareo_trabajado(df: pd.DataFrame, cfg: Config) -> bytes:
    """Exporta el intermedio REPORTE_TAREO_SISTEMA con las condiciones aplicadas."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    df = recalcular(df, cfg)
    cols = [c for c in ORDEN_TAREO_TRABAJADO if c in df.columns]

    wb = Workbook()
    ws = wb.active
    ws.title = "TAREO_TRABAJADO"
    header_fill = PatternFill("solid", fgColor="1F3864")
    header_font = Font(name="Calibri", color="FFFFFF", bold=True, size=9)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.append(cols)
    for c in range(1, len(cols) + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    for _, row in df[cols].iterrows():
        valores = []
        for col in cols:
            v = row[col]
            if col == "HORAS_MARCACION" and v is not None:
                try:
                    v = hours_to_hhmm(float(v)) if not (isinstance(v, float) and pd.isna(v)) else None
                except (TypeError, ValueError):
                    v = None
            elif col == "GRUPO" and v is not None:
                v = nombre_grupo(v)
            elif isinstance(v, float) and pd.isna(v):
                v = None
            valores.append(v)
        ws.append(valores)

    _left = Alignment(horizontal="left", vertical="center")
    _center = Alignment(horizontal="center", vertical="center")
    for r in range(2, ws.max_row + 1):
        for c, col in enumerate(cols, start=1):
            ws.cell(row=r, column=c).alignment = _left if col == "NOMBRES" else _center

    for c, col in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(c)].width = 30 if col == "NOMBRES" else 12
    ws.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
