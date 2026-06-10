"""
app.py
=================
Dashboard del Aplicativo de Tareo de Operaciones - PECEPE.

Flujo:
  1) Cargar REPORTE_TAREO_SISTEMA.xlsx (o usar el de la carpeta).
  2) Revisar / ajustar condiciones (Corrido C, Teorico 12, Descuento extra,
     Refrigerio) de forma masiva o individual con checks.
  3) Modulo de aprobacion del Coordinador de Operaciones: las horas teoricas
     se convierten en TTHH y se aprueban.
  4) Generar y descargar el REPORTE_OPERACIONES final.

Ejecutar:  streamlit run app.py
"""

import os

import pandas as pd
import streamlit as st

import tareo_core as core
import auth
import db
import dashboard_charts as dash

st.set_page_config(
    page_title="Tareo de Operaciones - PECEPE",
    page_icon="🕒",
    layout="wide",
)

RUTA_BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DEFECTO = os.path.join(RUTA_BASE, "REPORTE_TAREO_SISTEMA.xlsx")

# --------------------------------------------------------------------------- #
#  Estilos                                                                     #
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem;}
    .titulo-app {font-size: clamp(1.0rem, 4.5vw, 1.9rem); font-weight: 800; color: #1f3864; line-height: 1.2;}
    [data-testid="stMarkdownContainer"] svg { overflow: visible !important; }
    .sub {color:#5b6770;}
    .metric-card {background:#f1f5fb;border-radius:10px;padding:10px 14px;}
    div[data-testid="stDataFrame"] {border:1px solid #d9e1ec;border-radius:8px;}
    .pie-copy {text-align:center; color:#8a949e; font-size:0.8rem;
               margin-top:2.2rem; padding:0.6rem 0; border-top:1px solid #e6e9ee;}
    </style>
    """,
    unsafe_allow_html=True,
)

def mostrar_logo(altura: int = 56) -> None:
    st.markdown(
        f'<div style="font-family:\'Segoe UI\',Arial,sans-serif;font-weight:800;'
        f'font-size:{altura}px;color:#1F4E9B;line-height:1.0;'
        f'padding-bottom:6px;letter-spacing:-1px;">pecepe.</div>',
        unsafe_allow_html=True,
    )


def mostrar_pie() -> None:
    st.markdown(
        "<div class='pie-copy'>© APLICACIONES — DONET 2026</div>",
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
#  Estado                                                                      #
# --------------------------------------------------------------------------- #
# Inicializa esquema y usuarios por defecto en Supabase (idempotente, una vez)
if db.enabled() and "db_init" not in st.session_state:
    db.init_schema()
    auth.ensure_defaults()
    st.session_state.db_init = True

if "user" not in st.session_state:
    st.session_state.user = None
if "cfg" not in st.session_state:
    st.session_state.cfg = None  # se carga tras definir los helpers


def cargar_cfg_app() -> core.Config:
    if db.enabled():
        d = db.config_load()
        return core.Config.from_dict(d) if d else core.Config()
    return core.cargar_config()


def guardar_cfg_app(c: core.Config) -> None:
    if db.enabled():
        db.config_save(c.to_dict())
    else:
        core.guardar_config(c)


def cargar_estado_app():
    df = db.tareo_load() if db.enabled() else core.cargar_estado()
    if df is not None:
        # Añade las columnas calculadas (TTHH, TTHH_HHMM, INICIO/SALIDA, tramos)
        df = core.recalcular(df, st.session_state.cfg)
    return df


def reemplazar_estado(df) -> None:
    if db.enabled():
        db.tareo_replace(df)
    else:
        core.guardar_estado(df)


def borrar_estado_app() -> None:
    if db.enabled():
        db.tareo_truncate()
    else:
        core.borrar_estado()


if st.session_state.cfg is None:
    st.session_state.cfg = cargar_cfg_app()
if "tabla" not in st.session_state:
    st.session_state.tabla = None


def cfg() -> core.Config:
    return st.session_state.cfg


def persistir_subset(mask) -> None:
    """Guarda el avance. En DB sólo actualiza las filas del grupo (no pisa a otros);
    en local guarda toda la tabla."""
    if st.session_state.tabla is None:
        return
    if db.enabled():
        db.tareo_save_subset(st.session_state.tabla[mask])
    else:
        core.guardar_estado(st.session_state.tabla)


# --------------------------------------------------------------------------- #
#  Control de acceso (login)                                                   #
# --------------------------------------------------------------------------- #
if st.session_state.user is None:
    mostrar_logo(64)
    st.markdown(
        '<div class="titulo-app">🕒 Tareo de Operaciones</div>',
        unsafe_allow_html=True)
    st.markdown("#### Iniciar sesión")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Ingresar", type="primary")
    if ok:
        datos = auth.verificar(u, p)
        if datos:
            st.session_state.user = datos
            # Registro de auditoría al iniciar sesión
            if db.enabled():
                try:
                    _hdrs = st.context.headers
                    _ip   = (_hdrs.get("x-forwarded-for") or
                             _hdrs.get("x-real-ip") or "desconocida").split(",")[0].strip()
                    _ua   = _hdrs.get("user-agent") or ""
                    _ua_lo = _ua.lower()
                    if any(k in _ua_lo for k in ("iphone", "android", "mobile")):
                        _dev = "Celular"
                    elif any(k in _ua_lo for k in ("ipad", "tablet")):
                        _dev = "Tablet"
                    else:
                        _dev = "PC"
                    import uuid
                    _sk = str(uuid.uuid4())
                    _aid = db.registrar_login(
                        datos["usuario"], _ip, _dev, _ua[:500], _sk)
                    st.session_state["_audit_id"] = _aid
                    st.session_state["_audit_sk"] = _sk
                except Exception:
                    pass
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.caption(
        "Cada supervisor entra con su usuario y sólo verá **su grupo**. "
        "El coordinador ve y aprueba todos los grupos."
    )
    mostrar_pie()
    st.stop()

# Usuario autenticado
USER = st.session_state.user
ES_COORD   = USER["rol"] == "coordinador"
ES_VISOR   = USER["rol"] == "visualizador"
ES_AUDITOR = USER["rol"] == "auditor"
GRUPO_USER = USER.get("grupo")

# Carga el tareo compartido en cada recarga (refleja el trabajo de otros)
if not ES_AUDITOR:
    st.session_state.tabla = cargar_estado_app()


# --------------------------------------------------------------------------- #
#  Barra lateral: configuracion                                                #
# --------------------------------------------------------------------------- #
with st.sidebar:
    if ES_COORD:
        rol_txt = "Coordinador"
    elif ES_VISOR:
        rol_txt = "Visualizador"
    elif ES_AUDITOR:
        rol_txt = "Auditor"
    else:
        rol_txt = f"Supervisor · Grupo {GRUPO_USER}"
    st.markdown(f"👤 **{USER['usuario']}**  \n_{rol_txt}_")
    if st.button("🚪 Salir", type="primary", use_container_width=True):
        if db.enabled():
            try:
                _aid_out = st.session_state.get("_audit_id")
                if _aid_out:
                    db.registrar_logout(_aid_out)
            except Exception:
                pass
        st.session_state.clear()
        st.rerun()
    st.divider()

    if ES_AUDITOR:
        st.caption("Módulo de auditoría y control de accesos.")
    c = cfg()
    if ES_COORD:
        st.markdown("### ⚙️ Configuración de reglas")
        c.refrigerio_min = st.number_input("Refrigerio (minutos)", 0, 180, c.refrigerio_min, 5)
        grupos_txt = st.text_input(
            "Grupos SIN refrigerio (separados por coma)",
            ", ".join(c.grupos_sin_refrigerio),
            help="Estos grupos no descuentan refrigerio. Ej: E, PCP, N, 5, IQF",
        )
        c.grupos_sin_refrigerio = tuple(
            g.strip() for g in grupos_txt.split(",") if g.strip()
        )
        st.markdown("**Jornada teórica (OBS = 12)**")
        col1, col2 = st.columns(2)
        with col1:
            c.teorico_dia_inicio = st.text_input("Día inicio", c.teorico_dia_inicio)
        with col2:
            c.teorico_dia_salida = st.text_input("Día salida", c.teorico_dia_salida)
        st.caption("Opciones de jornada noche (se elige por persona/grupo en la pestaña 2):")
        op = c.jornada_noche_opciones
        claves = list(op.keys())
        n1a, n1b = st.columns(2)
        with n1a:
            a_ini = st.text_input("Noche A inicio", op[claves[0]][0])
        with n1b:
            a_sal = st.text_input("Noche A salida", op[claves[0]][1])
        n2a, n2b = st.columns(2)
        with n2a:
            b_ini = st.text_input("Noche B inicio", op[claves[1]][0])
        with n2b:
            b_sal = st.text_input("Noche B salida", op[claves[1]][1])
        c.jornada_noche_opciones = {
            f"{a_ini}-{a_sal}": (a_ini, a_sal),
            f"{b_ini}-{b_sal}": (b_ini, b_sal),
        }
        c.jornada_noche_default = st.selectbox(
            "Jornada noche por defecto", list(c.jornada_noche_opciones.keys()))
        st.markdown("**Reporte de Operaciones**")
        c.producto = st.text_input("PRODUCTO", c.producto)
        c.zona = st.text_input("ZONA", str(c.zona))
        if st.button("💾 Guardar reglas para todos"):
            guardar_cfg_app(c)
            st.success("Reglas guardadas.")
        st.caption("Tope hora normal: 8 h · Tramo 25%: hasta 10 h · 35%: el resto.")
    else:
        st.markdown("### ⚙️ Reglas vigentes")
        st.caption(
            f"Refrigerio: {c.refrigerio_min} min · "
            f"Sin refrigerio: {', '.join(c.grupos_sin_refrigerio)} · "
            f"Jornada noche: {', '.join(c.jornada_noche_opciones.keys())}"
        )
        st.caption("Definidas por el coordinador.")


# --------------------------------------------------------------------------- #
#  Encabezado                                                                  #
# --------------------------------------------------------------------------- #
mostrar_logo(48)
st.markdown('<div class="titulo-app">🕒 Tareo de Operaciones</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="sub">De <b>REPORTE_TAREO_SISTEMA</b> al <b>REPORTE_OPERACIONES</b> '
    "con cálculo automático de TTHH y horas extra.</div>",
    unsafe_allow_html=True,
)
st.write("")

if ES_AUDITOR:
    tab_auditoria, = st.tabs(["🔍 Auditoría"])
    (tab_cargar, tab_condiciones, tab_aprobacion, tab_reporte,
     tab_dashboard, tab_compartir, tab_users) = (
        None, None, None, None, None, None, None)
elif ES_COORD:
    (tab_cargar, tab_condiciones, tab_aprobacion, tab_reporte,
     tab_dashboard, tab_compartir, tab_users) = st.tabs(
        ["📥 1. Cargar", "🧮 2. Condiciones / TTHH", "✅ 3. Aprobación",
         "📤 4. Reporte final", "📊 Dashboard", "📱 Compartir", "👥 Usuarios"]
    )
    tab_auditoria = None
elif ES_VISOR:
    tab_cargar, tab_reporte, tab_dashboard, tab_compartir = st.tabs(
        ["📥 Cargar", "📤 Reporte final", "📊 Dashboard", "📱 Compartir"]
    )
    tab_condiciones = tab_aprobacion = tab_users = tab_auditoria = None
else:
    tab_condiciones, tab_aprobacion, tab_dashboard, tab_compartir = st.tabs(
        ["🧮 Condiciones / TTHH", "✅ Aprobación", "📊 Dashboard", "📱 Compartir"]
    )
    tab_cargar = tab_reporte = tab_users = tab_auditoria = None

# --------------------------------------------------------------------------- #
#  TAB 1: Cargar (sólo coordinador)                                            #
# --------------------------------------------------------------------------- #
if tab_cargar is not None:
    with tab_cargar:
        st.subheader("Cargar el archivo del sistema de asistencia")

        # --- Selector de periodo (año / mes / semana / días) ---------------- #
        with st.expander("📅 Periodo de trabajo", expanded=True):
            st.markdown(
                '<div style="background:linear-gradient(90deg,#1F4E9B,#1D4ED8);'
                'border-radius:8px;padding:10px 16px;margin-bottom:14px;">'
                '<span style="color:white;font-weight:700;font-size:0.95rem;">'
                '📅 &nbsp;Selecciona el periodo de trabajo</span></div>',
                unsafe_allow_html=True,
            )
            _ahora     = pd.Timestamp.now()
            _años      = list(range(2024, _ahora.year + 2))
            _mes_names = [dash.MESES_ES[i] for i in range(1, 13)]

            _pc1, _pc2, _pc3 = st.columns(3)
            with _pc1:
                _año_per = st.selectbox(
                    "Año", _años,
                    index=_años.index(_ahora.year), key="per_anio")
            with _pc2:
                _mes_nombre = st.selectbox(
                    "Mes", _mes_names,
                    index=_ahora.month - 1, key="per_mes")
                _mes_per = _mes_names.index(_mes_nombre) + 1

            _semanas  = dash.semanas_del_mes(_año_per, _mes_per)
            _sem_lbls = [s["label"] for s in _semanas]
            _sem_def  = 0
            if _año_per == _ahora.year and _mes_per == _ahora.month:
                _iso_now = _ahora.isocalendar()[1]
                for _i, _s in enumerate(_semanas):
                    if _s["num"] == _iso_now:
                        _sem_def = _i
                        break

            with _pc3:
                _sem_sel_lbl = st.selectbox(
                    "Semana ISO", _sem_lbls, index=_sem_def, key="per_semana")
            _sem_sel = _semanas[_sem_lbls.index(_sem_sel_lbl)]

            # Selector de día único (selectbox compacto, igual estilo que Año/Mes/Semana)
            _dia_opts = [
                f'{_dia["nombre"]} {_dia["fecha"].strftime("%d/%m/%Y")}'
                for _dia in _sem_sel["dias"]
            ]
            _dia_fecha_map = {
                f'{_dia["nombre"]} {_dia["fecha"].strftime("%d/%m/%Y")}': _dia["fecha"]
                for _dia in _sem_sel["dias"]
            }
            # Índice por defecto: hoy si está en la semana, si no el primer día del mes
            _def_dia = 0
            _hoy = _ahora.date()
            for _i, _dia in enumerate(_sem_sel["dias"]):
                if _dia["fecha"] == _hoy:
                    _def_dia = _i
                    break
            else:
                for _i, _dia in enumerate(_sem_sel["dias"]):
                    if _dia["en_mes"]:
                        _def_dia = _i
                        break

            _pc4, _pc5, _pc6 = st.columns(3)
            with _pc4:
                _dia_sel_str = st.selectbox(
                    "Día", _dia_opts, index=_def_dia, key="per_dia")
            _fecha_periodo = _dia_fecha_map[_dia_sel_str]
            _fechas_periodo = [_fecha_periodo]

            # Tarjeta de color para el día seleccionado
            _nom_dia = dash.DIAS_ES[_fecha_periodo.weekday()]
            _nom_mes = dash.MESES_ES[_fecha_periodo.month]
            st.markdown(
                f'<div style="background:#1F4E9B;color:white;border-radius:8px;'
                f'padding:10px 16px;margin-top:10px;font-weight:700;font-size:0.95rem;">'
                f'📅 &nbsp;{_nom_dia} {_fecha_periodo.day} de {_nom_mes} de {_fecha_periodo.year}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Guardar en session state para Dashboard y Aprobación
            st.session_state["_per_fechas"] = _fechas_periodo

        st.write("")
        archivo = st.file_uploader(
            "Sube el archivo de carga (sistema de asistencia)", type=["xlsx", "xls"]
        )
        usar_defecto = False
        if archivo is None and os.path.exists(ARCHIVO_DEFECTO):
            usar_defecto = st.checkbox(
                f"Usar el archivo de la carpeta ({os.path.basename(ARCHIVO_DEFECTO)})",
                value=True,
            )

        col_p, col_r = st.columns([1, 1])
        with col_p:
            if st.button("📊 Procesar tareo", type="primary"):
                try:
                    fuente = archivo if archivo is not None else (
                        ARCHIVO_DEFECTO if usar_defecto else None
                    )
                    if fuente is None:
                        st.error("Selecciona o sube un archivo primero.")
                    else:
                        df_sis = core.cargar_tareo_sistema(fuente)
                        tabla_nueva = core.construir_tabla_trabajo(df_sis, cfg())
                        # Si el Excel no trae fechas, usar la fecha del periodo seleccionado
                        _null_fecha = pd.to_datetime(tabla_nueva["FECHA"], errors="coerce").isna()
                        if _null_fecha.any() and _fechas_periodo:
                            tabla_nueva.loc[_null_fecha, "FECHA"] = pd.Timestamp(_fechas_periodo[0])
                        reemplazar_estado(tabla_nueva)
                        st.session_state.tabla = cargar_estado_app()
                        st.success(f"✅ Procesados {len(st.session_state.tabla)} registros. "
                                   "Los supervisores ya pueden trabajar sus grupos.")
                except Exception as e:
                    st.exception(e)
        with col_r:
            if st.button("🗑️ Reiniciar tareo (borrar todo)"):
                borrar_estado_app()
                st.session_state.tabla = None
                st.warning("Tareo reiniciado.")

        if st.session_state.tabla is not None:
            df = st.session_state.tabla

            # Filtrar vista por días seleccionados en el selector de periodo
            if _fechas_periodo:
                _mask_p = pd.to_datetime(
                    df["FECHA"], errors="coerce").dt.date.isin(_fechas_periodo)
                df_per = df[_mask_p]
            else:
                df_per = df

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Registros", len(df_per))
            c2.metric("Turno NOCHE", int((df_per["TURNO"] == "NOCHE").sum()))
            c3.metric("Corrido (C)", int(df_per["Corrido"].sum()))
            c4.metric("Teórico 12 h", int(df_per["Teorico12"].sum()))
            if len(df_per) < len(df):
                st.caption(
                    f"Periodo seleccionado: {len(df_per)} de {len(df)} "
                    "registros totales")
            elif not _fechas_periodo:
                st.warning("Selecciona al menos un día en el periodo de trabajo.")

            # Resumen semanal en tab Cargar
            df_sem_c = dash.agregar_cols_fecha(df_per)
            df_sem_c = df_sem_c.dropna(subset=["_SEMANA_NUM"])
            if not df_sem_c.empty:
                sem_tbl = df_sem_c.groupby(
                    ["_AÑO", "_SEMANA_NUM", "_SEMANA_LABEL"]
                ).agg(
                    Personas=("NOMBRES", "count"),
                    DIA=("TURNO", lambda x: (x == "DIA").sum()),
                    NOCHE=("TURNO", lambda x: (x == "NOCHE").sum()),
                ).reset_index().sort_values(["_AÑO", "_SEMANA_NUM"])
                sem_tbl = sem_tbl.rename(columns={"_SEMANA_LABEL": "Semana"})[
                    ["Semana", "Personas", "DIA", "NOCHE"]]
                with st.expander("📅 Resumen por semana del año", expanded=False):
                    st.dataframe(sem_tbl, use_container_width=True, hide_index=True)

            st.dataframe(
                df_per[["NOMBRES", "GRUPO", "SERVICE", "FECHA", "TURNO", "ENTRADA",
                    "SALIDA", "HORAS_MARC_HHMM"]],
                use_container_width=True, hide_index=True,
                column_config={
                    "FECHA": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                    "HORAS_MARC_HHMM": st.column_config.TextColumn("Horas marcación (hh:mm)"),
                    "ENTRADA": st.column_config.TextColumn("Entrada"),
                    "SALIDA": st.column_config.TextColumn("Salida"),
                },
            )

# --------------------------------------------------------------------------- #
#  TAB 2: Condiciones / TTHH                                                   #
# --------------------------------------------------------------------------- #
if tab_condiciones is not None:
 with tab_condiciones:
    if st.session_state.tabla is None:
        st.info("Primero carga y procesa el tareo en la pestaña 1.")
    else:
        st.subheader("Condiciones para convertir horas de marcación → TTHH")
        st.caption(
            "Cada supervisor filtra **su grupo** y marca las condiciones de forma "
            "**masiva** o **individual**. Corrido = sin refrigerio · "
            "Teórico 12 = jornada de 12 h · Descuento extra = horas a restar · "
            "Jornada noche = 19–07 o 20–08."
        )

        # --- Selector de grupo (coordinador) / bloqueado (supervisor) ----- #
        _grupos_data = st.session_state.tabla["GRUPO"].dropna().unique().tolist()
        grupos_disp = sorted(list(set([str(g) for g in _grupos_data] + auth.GRUPOS_POR_DEFECTO)), key=str)
        _fmt_g = lambda g: core.nombre_grupo(g) if g != "(Todos los grupos)" else g
        if ES_COORD:
            gsel = st.selectbox(
                "👷 Grupo (alcance de esta vista)",
                ["(Todos los grupos)"] + grupos_disp,
                format_func=_fmt_g, key="grupo_cond")
        else:
            gsel = str(GRUPO_USER)
            st.info(f"Estás autorizando el **grupo {core.nombre_grupo(gsel)}**.")
            if gsel not in [str(g) for g in grupos_disp]:
                st.warning("Tu grupo no tiene registros en el tareo cargado.")
        if gsel == "(Todos los grupos)":
            mask_g = pd.Series(True, index=st.session_state.tabla.index)
        else:
            mask_g = st.session_state.tabla["GRUPO"].astype(str) == gsel
        opciones_noche = list(cfg().jornada_noche_opciones.keys())

        # --- Acciones masivas (sólo sobre el grupo filtrado) -------------- #
        with st.expander(f"⚡ Acciones masivas — alcance: **{core.nombre_grupo(gsel) if gsel != '(Todos los grupos)' else gsel}**", expanded=True):
            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown("**Corrido (C)**")
                if st.button("✔ Todos", key="corr_all"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "Corrido", True, mask=mask_g)
                if st.button("✘ Quitar", key="q_corr"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "Corrido", False, mask=mask_g)
            with m2:
                st.markdown("**Teórico 12 h**")
                if st.button("✔ Todos", key="t12_all"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "Teorico12", True, mask=mask_g)
                if st.button("✘ Quitar", key="q_t12"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "Teorico12", False, mask=mask_g)
            with m3:
                st.markdown("**Refrigerio (45 min)**")
                if st.button("✔ Descontar", key="refri_all"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "Refrigerio", True, mask=mask_g)
                if st.button("✘ No descontar", key="q_refri"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "Refrigerio", False, mask=mask_g)

            m4, m5, m6 = st.columns(3)
            with m4:
                st.markdown("**Descuento extra (h)**")
                val = st.selectbox("Horas", [0.0, 1.0, 2.0, 3.0], key="desc_val",
                                   label_visibility="collapsed")
                if st.button("Aplicar a todos", key="desc_all"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "DescuentoExtra", float(val), mask=mask_g)
            with m5:
                st.markdown("**Aumento extra (h)**")
                vala = st.selectbox("Horas+", [0.0, 1.0, 2.0, 3.0], key="aum_val",
                                    label_visibility="collapsed")
                if st.button("Aplicar a todos", key="aum_all"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "AumentoExtra", float(vala), mask=mask_g)
            with m6:
                st.markdown("**Jornada noche (para Teórico 12)**")
                jn = st.selectbox("Jornada", opciones_noche, key="jn_val",
                                  label_visibility="collapsed")
                if st.button("Aplicar a turno noche", key="jn_all"):
                    mask_noche = mask_g & (st.session_state.tabla["TURNO"] == "NOCHE")
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "JornadaNoche", jn, mask=mask_noche)

        # --- Editor individual (sólo el grupo filtrado) ------------------- #
        st.markdown("#### Edición individual (check por persona)")
        df = core.recalcular(st.session_state.tabla, cfg())
        sub = df[mask_g]
        cols_edit = [
            "NOMBRES", "GRUPO", "TURNO", "ENTRADA", "SALIDA", "HORAS_MARC_HHMM",
            "Corrido", "Teorico12", "Refrigerio", "DescuentoExtra", "AumentoExtra",
            "JornadaNoche", "TTHH_HHMM", "TTHH",
        ]
        edited = st.data_editor(
            sub[cols_edit],
            use_container_width=True,
            hide_index=True,
            height=460,
            column_config={
                "NOMBRES": st.column_config.TextColumn("Nombre", disabled=True, width="large"),
                "GRUPO": st.column_config.TextColumn("Grupo", disabled=True),
                "TURNO": st.column_config.TextColumn("Turno", disabled=True),
                "ENTRADA": st.column_config.TextColumn("Entrada", disabled=True),
                "SALIDA": st.column_config.TextColumn("Salida", disabled=True),
                "HORAS_MARC_HHMM": st.column_config.TextColumn(
                    "Hrs marcación (hh:mm)", disabled=True),
                "Corrido": st.column_config.CheckboxColumn("Corrido (C)"),
                "Teorico12": st.column_config.CheckboxColumn("Teórico 12h"),
                "Refrigerio": st.column_config.CheckboxColumn("Desc. refrig."),
                "DescuentoExtra": st.column_config.SelectboxColumn(
                    "Desc. extra (h)", options=[0.0, 1.0, 2.0, 3.0]),
                "AumentoExtra": st.column_config.SelectboxColumn(
                    "Aum. extra (h)", options=[0.0, 1.0, 2.0, 3.0]),
                "JornadaNoche": st.column_config.SelectboxColumn(
                    "Jornada noche", options=opciones_noche),
                "TTHH_HHMM": st.column_config.TextColumn("TTHH (hh:mm)", disabled=True),
                "TTHH": st.column_config.NumberColumn("TTHH (dec)", disabled=True, format="%.2f"),
            },
            key=f"editor_condiciones_{gsel}",
        )
        # Persiste cambios de los checks editables (alineado por índice)
        for col in ["Corrido", "Teorico12", "Refrigerio", "DescuentoExtra",
                    "AumentoExtra", "JornadaNoche"]:
            st.session_state.tabla.loc[sub.index, col] = edited[col].values
        st.session_state.tabla = core.recalcular(st.session_state.tabla, cfg())
        persistir_subset(mask_g)  # comparte el avance (sólo este grupo en DB)

        total_tthh = st.session_state.tabla.loc[mask_g, "TTHH"].sum()
        st.success(f"TTHH del grupo **{gsel}**: {total_tthh:,.2f} h "
                   f"({core.hours_to_hhmm(total_tthh)}) · "
                   f"TTHH total: {st.session_state.tabla['TTHH'].sum():,.2f} h")

        st.download_button(
            "⬇️ Descargar REPORTE_TAREO_SISTEMA (trabajado).xlsx",
            data=core.exportar_tareo_trabajado(st.session_state.tabla, cfg()),
            file_name="REPORTE_TAREO_SISTEMA.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# --------------------------------------------------------------------------- #
#  TAB 3: Aprobación                                                           #
# --------------------------------------------------------------------------- #
if tab_aprobacion is not None:
 with tab_aprobacion:
    if st.session_state.tabla is None:
        st.info("Primero carga y procesa el tareo en la pestaña 1.")
    else:
        st.subheader("Módulo de aprobación por supervisor de grupo")
        st.caption(
            "Cada supervisor revisa las horas teóricas (TTHH) de **su grupo** y "
            "aprueba. Sólo lo aprobado pasa al REPORTE_OPERACIONES."
        )

        _grupos_data = st.session_state.tabla["GRUPO"].dropna().unique().tolist()
        grupos_disp = sorted(list(set([str(g) for g in _grupos_data] + auth.GRUPOS_POR_DEFECTO)), key=str)
        _fmt_g2 = lambda g: core.nombre_grupo(g) if g != "(Todos los grupos)" else g
        if ES_COORD:
            gsel = st.selectbox(
                "👷 Grupo", ["(Todos los grupos)"] + grupos_disp,
                format_func=_fmt_g2, key="grupo_aprob")
        else:
            gsel = str(GRUPO_USER)
            st.info(f"Estás aprobando el **grupo {core.nombre_grupo(gsel)}**.")
        if gsel == "(Todos los grupos)":
            mask_g = pd.Series(True, index=st.session_state.tabla.index)
        else:
            mask_g = st.session_state.tabla["GRUPO"].astype(str) == gsel

        # Filtro adicional por días del periodo activo (Tab 1)
        _per_fechas = st.session_state.get("_per_fechas", [])
        _per_str = ""
        if _per_fechas:
            _fecha_col = pd.to_datetime(
                st.session_state.tabla["FECHA"], errors="coerce").dt.date
            # Incluir registros con fecha coincidente O sin fecha (pertenecen al periodo actual)
            _mask_fecha = _fecha_col.isin(_per_fechas) | _fecha_col.isna()
            mask_g = mask_g & _mask_fecha
            _per_str = " · ".join(
                f"{dash.DIAS_ES[f.weekday()][:3]} {f.strftime('%d/%m/%Y')}"
                for f in _per_fechas
            )
            st.info(f"📅 Periodo activo: **{_per_str}**  \n"
                    "Solo se aprobarán los registros de esas fechas. "
                    "Para cambiar el periodo ve a la pestaña 📥 Cargar.")

        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("✅ Aprobar grupo", type="primary"):
                # Asignar fecha del periodo a registros sin fecha antes de guardar
                if _per_fechas:
                    _fill_f = pd.Timestamp(_per_fechas[0])
                    _null_m = mask_g & pd.to_datetime(
                        st.session_state.tabla["FECHA"], errors="coerce").isna()
                    if _null_m.any():
                        st.session_state.tabla.loc[_null_m, "FECHA"] = _fill_f
                _n = int(mask_g.sum())
                st.session_state.tabla = core.aplicar_masivo(
                    st.session_state.tabla, "Aprobado", True, mask=mask_g)
                persistir_subset(mask_g)
                st.success(
                    f"✅ **{_n} registros aprobados** y guardados en la base de datos."
                    + (f"  \nPeriodo: {_per_str}" if _per_str else "")
                )
        with a2:
            if st.button("❌ Desaprobar grupo"):
                _n = int(mask_g.sum())
                st.session_state.tabla = core.aplicar_masivo(
                    st.session_state.tabla, "Aprobado", False, mask=mask_g)
                persistir_subset(mask_g)
                st.warning(f"❌ {_n} registros desaprobados.")
        with a3:
            sub_t = st.session_state.tabla[mask_g]
            _gsel_nom = core.nombre_grupo(gsel) if gsel != "(Todos los grupos)" else gsel
            st.metric(f"Aprobados ({_gsel_nom})",
                      f"{int(sub_t['Aprobado'].sum())} / {len(sub_t)}")

        # Resumen de avance por grupo
        resumen = (st.session_state.tabla
                   .groupby("GRUPO")["Aprobado"]
                   .agg(["sum", "count"]).reset_index())
        resumen["Estado"] = resumen.apply(
            lambda r: "✅ Completo" if r["sum"] == r["count"]
            else (f"⏳ {int(r['sum'])}/{int(r['count'])}"), axis=1)
        resumen["Grupo"] = resumen["GRUPO"].map(core.nombre_grupo)
        st.dataframe(
            resumen.rename(columns={"sum": "Aprobados", "count": "Total"})[
                ["Grupo", "Aprobados", "Total", "Estado"]],
            use_container_width=True, hide_index=True,
        )

        df = core.recalcular(st.session_state.tabla, cfg())
        sub = df[mask_g]
        cols_apr = ["Aprobado", "NOMBRES", "GRUPO", "TURNO", "SERVICE",
                    "INICIO_FINAL", "SALIDA_FINAL", "TTHH_HHMM", "TTHH"]
        edited = st.data_editor(
            sub[cols_apr],
            use_container_width=True, hide_index=True, height=460,
            column_config={
                "Aprobado": st.column_config.CheckboxColumn("✅ Aprobado"),
                "NOMBRES": st.column_config.TextColumn("Nombre", disabled=True, width="large"),
                "GRUPO": st.column_config.TextColumn("Grupo", disabled=True),
                "TURNO": st.column_config.TextColumn("Turno", disabled=True),
                "SERVICE": st.column_config.TextColumn("Service", disabled=True),
                "INICIO_FINAL": st.column_config.TextColumn("Inicio", disabled=True),
                "SALIDA_FINAL": st.column_config.TextColumn("Salida", disabled=True),
                "TTHH_HHMM": st.column_config.TextColumn("TTHH (hh:mm)", disabled=True),
                "TTHH": st.column_config.NumberColumn("TTHH (dec)", disabled=True, format="%.2f"),
            },
            key=f"editor_aprobacion_{gsel}",
        )
        st.session_state.tabla.loc[sub.index, "Aprobado"] = edited["Aprobado"].values
        persistir_subset(mask_g)

# --------------------------------------------------------------------------- #
#  TAB 4: Reporte final (sólo coordinador)                                     #
# --------------------------------------------------------------------------- #
if tab_reporte is not None:
    with tab_reporte:
        if st.session_state.tabla is None:
            st.info("Primero carga y procesa el tareo en la pestaña 1.")
        else:
            st.subheader("REPORTE_OPERACIONES (producto final)")
            solo_aprob = st.checkbox("Incluir sólo registros aprobados", value=True)
            rep = core.generar_reporte_operaciones(
                st.session_state.tabla, cfg(), solo_aprobados=solo_aprob)

            if len(rep) == 0:
                st.warning("No hay registros aprobados aún. Los supervisores deben "
                           "aprobar sus grupos, o desmarca 'sólo aprobados'.")
            else:
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("Registros", len(rep))
                r2.metric("Horas total", f"{rep['horas total'].sum():,.1f}")
                r3.metric("Hora 25%", f"{rep['hora 25'].sum():,.1f}")
                r4.metric("Hora 35%", f"{rep['hora 35'].sum():,.1f}")

                # Resumen semanal en tab Reporte Final
                if "FECHA" in rep.columns:
                    df_sem_r = dash.agregar_cols_fecha(rep)
                    df_sem_r = df_sem_r.dropna(subset=["_SEMANA_NUM"])
                    if not df_sem_r.empty:
                        sem_rep = df_sem_r.groupby(
                            ["_AÑO", "_SEMANA_NUM", "_SEMANA_LABEL"]
                        ).agg(
                            Registros=("NOMBRES", "count"),
                            TTHH=("horas total", "sum"),
                            Hora_Normal=("hora normal", "sum"),
                            Hora_25=("hora 25", "sum"),
                            Hora_35=("hora 35", "sum"),
                        ).reset_index().sort_values(["_AÑO", "_SEMANA_NUM"])
                        sem_rep = sem_rep.rename(columns={
                            "_SEMANA_LABEL": "Semana",
                            "Hora_Normal": "Hora Normal",
                            "Hora_25": "Hora 25%",
                            "Hora_35": "Hora 35%",
                        })[["Semana", "Registros", "TTHH",
                            "Hora Normal", "Hora 25%", "Hora 35%"]]
                        with st.expander("📅 Resumen por semana del año", expanded=False):
                            st.dataframe(
                                sem_rep.style.format({
                                    "TTHH": "{:.2f}",
                                    "Hora Normal": "{:.2f}",
                                    "Hora 25%": "{:.2f}",
                                    "Hora 35%": "{:.2f}",
                                }),
                                use_container_width=True, hide_index=True,
                            )

                st.dataframe(rep, use_container_width=True, hide_index=True)

                xls = core.exportar_excel(rep)
                st.download_button(
                    "⬇️ Descargar REPORTE_OPERACIONES.xlsx",
                    data=xls,
                    file_name="REPORTE_OPERACIONES.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                )
                csv = rep.to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ Descargar CSV", data=csv,
                                   file_name="REPORTE_OPERACIONES.csv", mime="text/csv")

# --------------------------------------------------------------------------- #
#  TAB Usuarios (sólo coordinador): control de acceso por supervisor          #
# --------------------------------------------------------------------------- #
if tab_users is not None:
    with tab_users:
        st.subheader("Control de acceso — supervisores por grupo")
        st.caption("Crea/edita usuarios. Cada supervisor sólo verá su grupo al ingresar.")

        st.dataframe(pd.DataFrame(auth.listar()), use_container_width=True, hide_index=True)

        st.markdown("#### Crear o actualizar usuario")
        with st.form("nuevo_usuario"):
            cu1, cu2 = st.columns(2)
            with cu1:
                nu = st.text_input("Usuario")
                np_ = st.text_input("Contraseña (vacío = no cambiar)", type="password")
            with cu2:
                nrol = st.selectbox("Rol", ["supervisor", "coordinador"])
                ngrupo = st.text_input("Grupo (sólo supervisor, ej. N, E, PCP, 1..5, IQF)")
            guardar = st.form_submit_button("💾 Guardar usuario", type="primary")
        if guardar:
            if not nu.strip():
                st.error("Indica un nombre de usuario.")
            else:
                grupo_val = None if nrol == "coordinador" else (ngrupo.strip() or None)
                auth.crear_o_actualizar(nu, np_ or None, nrol, grupo_val)
                st.success(f"Usuario '{nu.strip().lower()}' guardado.")
                st.rerun()

        st.markdown("#### Eliminar usuario")
        usuarios = [u["usuario"] for u in auth.listar()]
        ce1, ce2 = st.columns([3, 1])
        with ce1:
            del_u = st.selectbox("Usuario a eliminar", usuarios)
        with ce2:
            st.write("")
            if st.button("🗑️ Eliminar"):
                if del_u == USER["usuario"]:
                    st.error("No puedes eliminar tu propio usuario en sesión.")
                else:
                    auth.eliminar(del_u)
                    st.warning(f"Usuario '{del_u}' eliminado.")
                    st.rerun()

# --------------------------------------------------------------------------- #
#  TAB AUDITORÍA (sólo rol "auditor")                                          #
# --------------------------------------------------------------------------- #
if tab_auditoria is not None:
    with tab_auditoria:
        st.subheader("🔍 Registro de accesos — Auditoría")
        if not db.enabled():
            st.warning("La auditoría requiere base de datos (DATABASE_URL no configurada).")
        else:
            try:
                df_aud = db.auditoria_load()
                if df_aud.empty:
                    st.info("No hay registros de acceso todavía.")
                else:
                    df_aud = df_aud.rename(columns={
                        "usuario":      "Usuario",
                        "entrada":      "Fecha/Hora Entrada",
                        "salida":       "Fecha/Hora Salida",
                        "duracion_min": "Duración (min)",
                        "ip":           "IP",
                        "dispositivo":  "Dispositivo",
                        "user_agent":   "User-Agent",
                    })
                    if "Duración (min)" in df_aud.columns:
                        df_aud["Duración (min)"] = df_aud["Duración (min)"].apply(
                            lambda x: f"{x:.1f}" if pd.notna(x) else "Activo")
                    total   = len(df_aud)
                    activos = (df_aud["Duración (min)"] == "Activo").sum()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total sesiones",  total)
                    m2.metric("Sesiones activas", activos)
                    m3.metric("Usuarios únicos",  df_aud["Usuario"].nunique())
                    cols_mostrar = ["Usuario", "Fecha/Hora Entrada", "Fecha/Hora Salida",
                                    "Duración (min)", "IP", "Dispositivo"]
                    st.dataframe(df_aud[cols_mostrar],
                                 use_container_width=True, hide_index=True)
                    with st.expander("Ver detalle completo (User-Agent)"):
                        st.dataframe(df_aud, use_container_width=True, hide_index=True)
                    if st.button("🔄 Actualizar"):
                        st.rerun()
            except Exception as _e:
                st.error(f"Error cargando auditoría: {_e}")
    mostrar_pie()
    st.stop()

# --------------------------------------------------------------------------- #
#  TAB Dashboard (coordinador y supervisor)                                    #
# --------------------------------------------------------------------------- #
with tab_dashboard:
    # Auto-cargar desde DB si la sesión aún no tiene datos (acceso directo al dashboard)
    _dash_src = st.session_state.tabla
    if _dash_src is None and db.enabled():
        try:
            _raw = db.tareo_load()
            if _raw is not None:
                _dash_src = core.recalcular(_raw, cfg())
        except Exception:
            _dash_src = None

    if _dash_src is None:
        st.info("No hay datos disponibles. Carga el tareo en la pestaña 1.")
    else:
        df_dash = core.recalcular(_dash_src, cfg())

        # --- Filtros -------------------------------------------------------- #
        st.markdown("### 🔍 Filtros del Dashboard")
        _grupos_data = df_dash["GRUPO"].dropna().unique().tolist()
        grupos_disp_dash = sorted(list(set([str(g) for g in _grupos_data] + auth.GRUPOS_POR_DEFECTO)), key=str)
        col_f1, col_f2, col_f3 = st.columns([3, 1, 1])
        with col_f1:
            if ES_COORD:
                grupos_sel = st.multiselect(
                    "Grupos a visualizar", grupos_disp_dash,
                    default=grupos_disp_dash,
                    format_func=core.nombre_grupo, key="dash_grupos")
            else:
                grupos_sel = [str(GRUPO_USER)]
                st.info(f"Visualizando grupo: **{core.nombre_grupo(GRUPO_USER)}**")
        with col_f2:
            turno_sel = st.selectbox(
                "Turno", ["Todos", "DIA", "NOCHE"], key="dash_turno")
        with col_f3:
            apro_sel = st.selectbox(
                "Aprobado", ["Todos", "Aprobados", "Pendientes"], key="dash_apro")

        # --- Filtros de fecha / semana ISO / día ----------------------------- #
        df_dash_f = dash.agregar_cols_fecha(df_dash)
        años_disp = sorted(df_dash_f["_AÑO"].dropna().unique().tolist())

        _df1, _df2, _df3 = st.columns(3)
        with _df1:
            año_sel = st.selectbox(
                "Año", ["Todos"] + [int(a) for a in años_disp], key="dash_anio")
        with _df2:
            meses_disp = sorted(df_dash_f["_MES_NUM"].dropna().unique().tolist())
            meses_opts = [dash.MESES_ES.get(int(m), str(m)) for m in meses_disp]
            meses_sel_names = st.multiselect(
                "Mes", meses_opts, default=meses_opts, key="dash_meses")
            meses_sel_nums = [
                k for k, v in dash.MESES_ES.items() if v in meses_sel_names]
        with _df3:
            # Semanas filtradas por año y mes ya seleccionados
            _ms_tmp = pd.Series(True, index=df_dash_f.index)
            if año_sel != "Todos":
                _ms_tmp &= df_dash_f["_AÑO"] == int(año_sel)
            if meses_sel_nums:
                _ms_tmp &= df_dash_f["_MES_NUM"].isin(meses_sel_nums)
            sems_disp = (
                df_dash_f[_ms_tmp & (df_dash_f["_SEMANA_LABEL"] != "")]["_SEMANA_LABEL"]
                .drop_duplicates().sort_values().tolist()
            )
            sems_sel = st.multiselect(
                "Semana ISO", sems_disp, default=sems_disp, key="dash_semanas")

        # Máscara parcial: grupo + turno + aprobado + año + mes + semana
        mask_partial = df_dash_f["GRUPO"].isin(grupos_sel)
        if turno_sel != "Todos":
            mask_partial &= df_dash_f["TURNO"] == turno_sel
        if apro_sel == "Aprobados" and "Aprobado" in df_dash_f.columns:
            mask_partial &= df_dash_f["Aprobado"] == True
        elif apro_sel == "Pendientes" and "Aprobado" in df_dash_f.columns:
            mask_partial &= df_dash_f["Aprobado"] == False
        if año_sel != "Todos":
            mask_partial &= df_dash_f["_AÑO"] == int(año_sel)
        if meses_sel_nums:
            mask_partial &= df_dash_f["_MES_NUM"].isin(meses_sel_nums)
        if sems_sel:
            mask_partial &= df_dash_f["_SEMANA_LABEL"].isin(sems_sel)

        # Filtro de días específicos (se sincroniza con el periodo de Tab 1)
        _periodo_fechas = st.session_state.get("_per_fechas", [])
        _fechas_en_filtro = sorted(
            pd.to_datetime(df_dash_f.loc[mask_partial, "FECHA"], errors="coerce")
            .dt.date.dropna().unique()
        )
        if _fechas_en_filtro:
            _dias_fmt = {
                f"{dash.DIAS_ES[f.weekday()][:3].upper()} {f.strftime('%d/%m')}": f
                for f in _fechas_en_filtro
            }
            _default_dias = (
                [lbl for lbl, f in _dias_fmt.items() if f in _periodo_fechas]
                or list(_dias_fmt.keys())
            )
            _dias_sel_lbls = st.multiselect(
                "Días específicos", list(_dias_fmt.keys()),
                default=_default_dias, key="dash_dias",
            )
            _fechas_sel = [_dias_fmt[lbl] for lbl in _dias_sel_lbls]
            mask_dash = mask_partial.copy()
            if _fechas_sel:
                mask_dash &= (
                    pd.to_datetime(df_dash_f["FECHA"], errors="coerce")
                    .dt.date.isin(_fechas_sel)
                )
        else:
            mask_dash = mask_partial

        df_f = df_dash_f[mask_dash]

        if len(df_f) == 0:
            st.warning("Sin datos para los filtros seleccionados.")
        else:
            # --- KPIs generales --------------------------------------------- #
            st.divider()
            st.markdown("### 📈 Indicadores Generales")
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("👥 Registros", len(df_f))
            k2.metric("⏱️ TTHH Total", f"{df_f['TTHH'].sum():,.1f} h")
            k3.metric("📈 Hora 25%", f"{df_f['hora 25'].sum():,.1f} h")
            k4.metric("📈 Hora 35%", f"{df_f['hora 35'].sum():,.1f} h")
            pct_apr = (f"{df_f['Aprobado'].mean()*100:.0f}%"
                       if "Aprobado" in df_f.columns else "—")
            k5.metric("✅ Aprobado", pct_apr)

            # --- Sección A: Tareo Original ----------------------------------- #
            st.divider()
            st.markdown(
                "### 📥 Tareo Original — Distribución y Condiciones  \n"
                "<small style='color:#5b6770;'>Pasa el cursor sobre los gráficos "
                "para ver detalle · Usa el ícono 📷 para descargar como PNG</small>",
                unsafe_allow_html=True,
            )
            a1, a2 = st.columns(2)
            with a1:
                st.plotly_chart(
                    dash.graf_turnos(df_f),
                    use_container_width=True,
                    config=dash._PNG_CFG,
                )
            with a2:
                st.plotly_chart(
                    dash.graf_registros_grupo(df_f),
                    use_container_width=True,
                    config=dash._PNG_CFG,
                )
            a3, a4 = st.columns(2)
            with a3:
                st.plotly_chart(
                    dash.graf_condiciones(df_f),
                    use_container_width=True,
                    config=dash._PNG_CFG,
                )
            with a4:
                st.plotly_chart(
                    dash.graf_horas_marc_grupo(df_f),
                    use_container_width=True,
                    config=dash._PNG_CFG,
                )

            # --- Sección B: Tareo Final -------------------------------------- #
            st.divider()
            st.markdown("### 📤 Tareo Final — TTHH y Aprobación")
            b1, b2 = st.columns(2)
            with b1:
                st.plotly_chart(
                    dash.graf_tthh_grupo(df_f),
                    use_container_width=True,
                    config=dash._PNG_CFG,
                )
            with b2:
                st.plotly_chart(
                    dash.graf_dist_horas(df_f),
                    use_container_width=True,
                    config=dash._PNG_CFG,
                )
            if "Aprobado" in df_f.columns:
                st.plotly_chart(
                    dash.graf_aprobacion(df_f),
                    use_container_width=True,
                    config=dash._PNG_CFG,
                )

            # --- Sección C: Análisis Temporal por Semana -------------------- #
            st.divider()
            st.markdown("### 📅 Análisis Temporal — Por Semana del Año")
            if "_SEMANA_NUM" not in df_f.columns or df_f["_SEMANA_NUM"].isna().all():
                st.info("Sin columna FECHA con fechas válidas para el análisis semanal.")
            else:
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(
                        dash.graf_registros_semana(df_f),
                        use_container_width=True,
                        config=dash._PNG_CFG,
                    )
                with c2:
                    st.plotly_chart(
                        dash.graf_tthh_semana(df_f),
                        use_container_width=True,
                        config=dash._PNG_CFG,
                    )
                # Tabla resumen semanal
                df_sem = df_f.dropna(subset=["_SEMANA_NUM"]).copy()
                resumen_sem = df_sem.groupby(
                    ["_AÑO", "_SEMANA_NUM", "_SEMANA_LABEL"]
                ).agg(
                    Personas=("NOMBRES", "count"),
                    DIA=("TURNO", lambda x: (x == "DIA").sum()),
                    NOCHE=("TURNO", lambda x: (x == "NOCHE").sum()),
                    TTHH=("TTHH", "sum"),
                    Hora_Normal=("hora normal", "sum"),
                    Hora_25=("hora 25", "sum"),
                    Hora_35=("hora 35", "sum"),
                ).reset_index().sort_values(["_AÑO", "_SEMANA_NUM"])
                resumen_sem = resumen_sem.rename(columns={
                    "_SEMANA_LABEL": "Semana",
                    "Hora_Normal": "Hora Normal",
                    "Hora_25": "Hora 25%",
                    "Hora_35": "Hora 35%",
                })[["Semana", "Personas", "DIA", "NOCHE",
                    "TTHH", "Hora Normal", "Hora 25%", "Hora 35%"]]
                st.markdown("#### Resumen por Semana")
                st.dataframe(
                    resumen_sem.style.format({
                        "TTHH": "{:.2f}",

                        "Hora Normal": "{:.2f}",
                        "Hora 25%": "{:.2f}",
                        "Hora 35%": "{:.2f}",
                    }),
                    use_container_width=True, hide_index=True,
                )

            # --- Descarga PDF de gráficos ----------------------------------- #
            st.divider()
            st.markdown("### 📄 Descargar gráficos en PDF")
            _coord_pdf = USER["usuario"] if ES_COORD else ""
            _sup_pdf   = USER["usuario"] if not ES_COORD else ""
            _pdf_graf = dash.generar_pdf_graficos(
                df_f, "INFORME DE OPERACIONES — PECEPE",
                coordinador=_coord_pdf, supervisor=_sup_pdf)
            st.download_button(
                "⬇️ Descargar PDF — Gráficos del Dashboard (A4)",
                data=_pdf_graf,
                file_name="graficos_dashboard.pdf",
                mime="application/pdf",
                key="dl_pdf_graficos_dash",
            )


# --------------------------------------------------------------------------- #
#  TAB Compartir por WhatsApp                                                  #
# --------------------------------------------------------------------------- #
with tab_compartir:
    st.subheader("📱 Compartir por WhatsApp")
    st.caption(
        "Genera mensajes formateados o descarga archivos para compartir "
        "el tareo y el reporte de operaciones directamente desde WhatsApp."
    )

    if st.session_state.tabla is None:
        st.info("Primero carga y procesa el tareo en la pestaña 1.")
    else:
        df_wa = core.recalcular(st.session_state.tabla, cfg())
        if not ES_COORD:
            df_wa = df_wa[df_wa["GRUPO"].astype(str) == str(GRUPO_USER)]

        # --- Resumen del tareo ---------------------------------------------- #
        with st.expander("📋 Resumen General del Tareo", expanded=True):
            titulo_wa = (
                "RESUMEN TAREO"
                if ES_COORD else f"TAREO — GRUPO {GRUPO_USER}"
            )
            txt_resumen = dash.texto_resumen(df_wa, titulo_wa)
            st.text_area(
                "Vista previa del mensaje:",
                txt_resumen, height=280, disabled=True,
                key="wa_resumen_prev",
            )
            st.markdown(
                dash.boton_wa_html(
                    dash.url_wa(txt_resumen),
                    "💬 Abrir WhatsApp — Resumen Tareo",
                ),
                unsafe_allow_html=True,
            )
            st.caption(
                "El botón abre WhatsApp Web (o la app en móvil) con el "
                "mensaje listo. Elige el contacto o grupo y envía."
            )

        # --- Reporte de operaciones (solo coordinador) ---------------------- #
        if ES_COORD:
            with st.expander("📤 Reporte de Operaciones Final"):
                rep_wa = core.generar_reporte_operaciones(
                    st.session_state.tabla, cfg(), solo_aprobados=True)
                if len(rep_wa) == 0:
                    st.warning(
                        "No hay registros aprobados aún. "
                        "Los supervisores deben aprobar sus grupos en la pestaña 3.")
                else:
                    txt_rep = dash.texto_reporte_final(rep_wa)
                    st.text_area(
                        "Vista previa:", txt_rep, height=280, disabled=True,
                        key="wa_rep_prev",
                    )
                    st.markdown(
                        dash.boton_wa_html(
                            dash.url_wa(txt_rep),
                            "💬 Abrir WhatsApp — Reporte Final",
                        ),
                        unsafe_allow_html=True,
                    )

        # --- Archivos para adjuntar ----------------------------------------- #
        with st.expander("📁 Descargar archivos para adjuntar en WhatsApp"):
            st.caption(
                "Descarga los archivos Excel y adjúntalos directamente "
                "en tu conversación de WhatsApp."
            )
            xls_tareo = core.exportar_tareo_trabajado(df_wa, cfg())
            st.download_button(
                "⬇️ Descargar Tareo Trabajado (.xlsx)",
                data=xls_tareo,
                file_name="REPORTE_TAREO_SISTEMA.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            if ES_COORD:
                rep_xl = core.generar_reporte_operaciones(
                    st.session_state.tabla, cfg(), solo_aprobados=True)
                if len(rep_xl) > 0:
                    st.download_button(
                        "⬇️ Descargar Reporte Final (.xlsx)",
                        data=core.exportar_excel(rep_xl),
                        file_name="REPORTE_OPERACIONES.xlsx",
                        mime=(
                            "application/vnd.openxmlformats-officedocument"
                            ".spreadsheetml.sheet"
                        ),
                    )
            _coord_wa = USER["usuario"] if ES_COORD else ""
            _sup_wa   = USER["usuario"] if not ES_COORD else ""
            _pdf_graf_wa = dash.generar_pdf_graficos(
                df_wa, "INFORME DE OPERACIONES — PECEPE",
                coordinador=_coord_wa, supervisor=_sup_wa)
            st.download_button(
                "⬇️ Descargar PDF — Gráficos del Dashboard",
                data=_pdf_graf_wa,
                file_name="graficos_dashboard.pdf",
                mime="application/pdf",
                key="dl_pdf_graficos_wa",
            )

        # --- PDF para compartir (PC / tablet / celular) --------------------- #
        with st.expander("📄 Compartir PDF — PC · Tablet · Celular", expanded=False):
            st.markdown(
                "Genera un PDF resumido y descárgalo para adjuntarlo en WhatsApp "
                "desde cualquier dispositivo."
            )
            _titulo_pdf = ("RESUMEN TAREO" if ES_COORD
                           else f"TAREO — GRUPO {GRUPO_USER}")
            _pdf_bytes = dash.generar_pdf_resumen(df_wa, _titulo_pdf)
            st.download_button(
                "⬇️ Descargar PDF — Resumen del Tareo",
                data=_pdf_bytes,
                file_name="tareo_pecepe.pdf",
                mime="application/pdf",
                key="dl_pdf_resumen",
            )
            if ES_COORD:
                _rep_pdf = core.generar_reporte_operaciones(
                    st.session_state.tabla, cfg(), solo_aprobados=True)
                if len(_rep_pdf) > 0:
                    _pdf_rep = dash.generar_pdf_resumen(
                        _rep_pdf, "REPORTE OPERACIONES FINAL")
                    st.download_button(
                        "⬇️ Descargar PDF — Reporte Final",
                        data=_pdf_rep,
                        file_name="reporte_operaciones.pdf",
                        mime="application/pdf",
                        key="dl_pdf_reporte",
                    )

            # PDF de gráficos del Dashboard
            _coord_comp = USER["usuario"] if ES_COORD else ""
            _sup_comp   = USER["usuario"] if not ES_COORD else ""
            _pdf_graf_comp = dash.generar_pdf_graficos(
                df_wa, "INFORME DE OPERACIONES — PECEPE",
                coordinador=_coord_comp, supervisor=_sup_comp)
            st.download_button(
                "⬇️ Descargar PDF — Gráficos del Dashboard",
                data=_pdf_graf_comp,
                file_name="graficos_dashboard.pdf",
                mime="application/pdf",
                key="dl_pdf_graficos_comp",
            )

            st.divider()
            _tab_pc, _tab_mov = st.tabs(
                ["💻 PC – WhatsApp Web", "📱 Celular / Tablet"])
            with _tab_pc:
                st.markdown(
                    "**Pasos para compartir el PDF desde la computadora:**\n"
                    "1. Haz clic en **Descargar PDF** (arriba) → "
                    "se guarda en tu carpeta *Descargas*\n"
                    "2. Abre **WhatsApp Web** en tu navegador\n"
                    "3. Selecciona la conversación o grupo\n"
                    "4. Haz clic en el ícono 📎 **(adjuntar)** en la barra inferior\n"
                    "5. Elige **Documento** y selecciona el PDF descargado\n"
                    "6. Envía el mensaje"
                )
            with _tab_mov:
                st.markdown(
                    "**Pasos para compartir el PDF desde celular o tablet:**\n\n"
                    "**Opción A — desde WhatsApp:**\n"
                    "1. Toca **Descargar PDF** (arriba) → "
                    "el archivo se guarda en *Descargas*\n"
                    "2. Abre WhatsApp → conversación o grupo\n"
                    "3. Toca el ícono **+** o 📎 → **Documento**\n"
                    "4. Busca el PDF en *Descargas* → envía\n\n"
                    "**Opción B — compartir directo desde Descargas:**\n"
                    "1. Descarga el PDF con el botón de arriba\n"
                    "2. Abre la app **Archivos** o **Descargas** del celular\n"
                    "3. Mantén presionado el PDF → toca **Compartir**\n"
                    "4. Elige **WhatsApp** → selecciona contacto o grupo → envía"
                )


# --------------------------------------------------------------------------- #
#  Pie de página (copyright)                                                   #
# --------------------------------------------------------------------------- #
mostrar_pie()
