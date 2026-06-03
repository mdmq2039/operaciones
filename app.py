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
    .titulo-app {font-size: 1.9rem; font-weight: 800; color: #1f3864;}
    .sub {color:#5b6770;}
    .metric-card {background:#f1f5fb;border-radius:10px;padding:10px 14px;}
    div[data-testid="stDataFrame"] {border:1px solid #d9e1ec;border-radius:8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
#  Estado                                                                      #
# --------------------------------------------------------------------------- #
if "user" not in st.session_state:
    st.session_state.user = None
if "cfg" not in st.session_state:
    st.session_state.cfg = core.cargar_config()
if "tabla" not in st.session_state:
    st.session_state.tabla = None


def cfg() -> core.Config:
    return st.session_state.cfg


def persistir_tabla() -> None:
    """Guarda el tareo compartido para que todos los supervisores lo vean."""
    if st.session_state.tabla is not None:
        core.guardar_estado(st.session_state.tabla)


# --------------------------------------------------------------------------- #
#  Control de acceso (login)                                                   #
# --------------------------------------------------------------------------- #
if st.session_state.user is None:
    st.markdown(
        '<div style="font-size:1.9rem;font-weight:800;color:#1f3864;">'
        '🕒 Tareo de Operaciones — PECEPE</div>', unsafe_allow_html=True)
    st.markdown("#### Iniciar sesión")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Ingresar", type="primary")
    if ok:
        datos = auth.verificar(u, p)
        if datos:
            st.session_state.user = datos
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.caption(
        "Cada supervisor entra con su usuario y sólo verá **su grupo**. "
        "El coordinador ve y aprueba todos los grupos."
    )
    st.stop()

# Usuario autenticado
USER = st.session_state.user
ES_COORD = USER["rol"] == "coordinador"
GRUPO_USER = USER.get("grupo")

# Carga el tareo compartido en cada recarga (refleja el trabajo de otros)
st.session_state.tabla = core.cargar_estado()


# --------------------------------------------------------------------------- #
#  Barra lateral: configuracion                                                #
# --------------------------------------------------------------------------- #
with st.sidebar:
    rol_txt = "Coordinador" if ES_COORD else f"Supervisor · Grupo {GRUPO_USER}"
    st.markdown(f"👤 **{USER['usuario']}**  \n_{rol_txt}_")
    if st.button("Cerrar sesión"):
        st.session_state.user = None
        st.rerun()
    st.divider()

    c = cfg()
    if ES_COORD:
        st.markdown("### ⚙️ Configuración de reglas")
        c.refrigerio_min = st.number_input("Refrigerio (minutos)", 0, 180, c.refrigerio_min, 5)
        grupos_txt = st.text_input(
            "Grupos SIN refrigerio (separados por coma)",
            ", ".join(c.grupos_sin_refrigerio),
            help="Estos grupos no descuentan refrigerio. Ej: E, PCP, N, 5",
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
            core.guardar_config(c)
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
st.markdown('<div class="titulo-app">🕒 Tareo de Operaciones — PECEPE</div>',
            unsafe_allow_html=True)
st.markdown(
    '<div class="sub">De <b>REPORTE_TAREO_SISTEMA</b> al <b>REPORTE_OPERACIONES</b> '
    "con cálculo automático de TTHH y horas extra.</div>",
    unsafe_allow_html=True,
)
st.write("")

if ES_COORD:
    tab_cargar, tab_condiciones, tab_aprobacion, tab_reporte, tab_users = st.tabs(
        ["📥 1. Cargar", "🧮 2. Condiciones / TTHH", "✅ 3. Aprobación",
         "📤 4. Reporte final", "👥 Usuarios"]
    )
else:
    tab_condiciones, tab_aprobacion = st.tabs(
        ["🧮 Condiciones / TTHH", "✅ Aprobación"]
    )
    tab_cargar = tab_reporte = tab_users = None

# --------------------------------------------------------------------------- #
#  TAB 1: Cargar (sólo coordinador)                                            #
# --------------------------------------------------------------------------- #
if tab_cargar is not None:
    with tab_cargar:
        st.subheader("Cargar el archivo del sistema de asistencia")
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
                        st.session_state.tabla = core.construir_tabla_trabajo(df_sis, cfg())
                        persistir_tabla()
                        st.success(f"✅ Procesados {len(st.session_state.tabla)} registros. "
                                   "Los supervisores ya pueden trabajar sus grupos.")
                except Exception as e:
                    st.exception(e)
        with col_r:
            if st.button("🗑️ Reiniciar tareo (borrar todo)"):
                core.borrar_estado()
                st.session_state.tabla = None
                st.warning("Tareo reiniciado.")

        if st.session_state.tabla is not None:
            df = st.session_state.tabla
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Registros", len(df))
            c2.metric("Turno NOCHE", int((df["TURNO"] == "NOCHE").sum()))
            c3.metric("Corrido (C)", int(df["Corrido"].sum()))
            c4.metric("Teórico 12 h", int(df["Teorico12"].sum()))
            st.dataframe(
                df[["NOMBRES", "GRUPO", "SERVICE", "TURNO", "ENTRADA", "SALIDA",
                    "HORAS_MARCACION", "OBSERVACION", "TTHH_HHMM"]],
                use_container_width=True, hide_index=True,
            )

# --------------------------------------------------------------------------- #
#  TAB 2: Condiciones / TTHH                                                   #
# --------------------------------------------------------------------------- #
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
        grupos_disp = sorted(st.session_state.tabla["GRUPO"].unique().tolist(), key=str)
        if ES_COORD:
            gsel = st.selectbox(
                "👷 Grupo (alcance de esta vista)",
                ["(Todos los grupos)"] + grupos_disp, key="grupo_cond")
        else:
            gsel = str(GRUPO_USER)
            st.info(f"Estás autorizando el **grupo {gsel}**.")
            if gsel not in [str(g) for g in grupos_disp]:
                st.warning("Tu grupo no tiene registros en el tareo cargado.")
        if gsel == "(Todos los grupos)":
            mask_g = pd.Series(True, index=st.session_state.tabla.index)
        else:
            mask_g = st.session_state.tabla["GRUPO"].astype(str) == gsel
        opciones_noche = list(cfg().jornada_noche_opciones.keys())

        # --- Acciones masivas (sólo sobre el grupo filtrado) -------------- #
        with st.expander(f"⚡ Acciones masivas — alcance: **{gsel}**", expanded=True):
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

            m4, m5 = st.columns(2)
            with m4:
                st.markdown("**Descuento extra (h)**")
                val = st.selectbox("Horas", [0.0, 1.0, 2.0, 3.0], key="desc_val",
                                   label_visibility="collapsed")
                if st.button("Aplicar a todos", key="desc_all"):
                    st.session_state.tabla = core.aplicar_masivo(
                        st.session_state.tabla, "DescuentoExtra", float(val), mask=mask_g)
            with m5:
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
            "NOMBRES", "GRUPO", "TURNO", "ENTRADA", "SALIDA", "HORAS_MARCACION",
            "Corrido", "Teorico12", "Refrigerio", "DescuentoExtra", "JornadaNoche",
            "OBSERVACION", "TTHH_HHMM", "TTHH",
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
                "HORAS_MARCACION": st.column_config.NumberColumn(
                    "Hrs marcación", disabled=True, format="%.2f"),
                "Corrido": st.column_config.CheckboxColumn("Corrido (C)"),
                "Teorico12": st.column_config.CheckboxColumn("Teórico 12h"),
                "Refrigerio": st.column_config.CheckboxColumn("Desc. refrig."),
                "DescuentoExtra": st.column_config.SelectboxColumn(
                    "Desc. extra (h)", options=[0.0, 1.0, 2.0, 3.0]),
                "JornadaNoche": st.column_config.SelectboxColumn(
                    "Jornada noche", options=opciones_noche),
                "OBSERVACION": st.column_config.TextColumn("Obs. original", disabled=True),
                "TTHH_HHMM": st.column_config.TextColumn("TTHH (hh:mm)", disabled=True),
                "TTHH": st.column_config.NumberColumn("TTHH (dec)", disabled=True, format="%.2f"),
            },
            key=f"editor_condiciones_{gsel}",
        )
        # Persiste cambios de los checks editables (alineado por índice)
        for col in ["Corrido", "Teorico12", "Refrigerio", "DescuentoExtra", "JornadaNoche"]:
            st.session_state.tabla.loc[sub.index, col] = edited[col].values
        st.session_state.tabla = core.recalcular(st.session_state.tabla, cfg())
        persistir_tabla()  # comparte el avance con el coordinador y otros

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
with tab_aprobacion:
    if st.session_state.tabla is None:
        st.info("Primero carga y procesa el tareo en la pestaña 1.")
    else:
        st.subheader("Módulo de aprobación por supervisor de grupo")
        st.caption(
            "Cada supervisor revisa las horas teóricas (TTHH) de **su grupo** y "
            "aprueba. Sólo lo aprobado pasa al REPORTE_OPERACIONES."
        )

        grupos_disp = sorted(st.session_state.tabla["GRUPO"].unique().tolist(), key=str)
        if ES_COORD:
            gsel = st.selectbox(
                "👷 Grupo", ["(Todos los grupos)"] + grupos_disp, key="grupo_aprob")
        else:
            gsel = str(GRUPO_USER)
            st.info(f"Estás aprobando el **grupo {gsel}**.")
        if gsel == "(Todos los grupos)":
            mask_g = pd.Series(True, index=st.session_state.tabla.index)
        else:
            mask_g = st.session_state.tabla["GRUPO"].astype(str) == gsel

        a1, a2, a3 = st.columns(3)
        with a1:
            if st.button("✅ Aprobar grupo", type="primary"):
                st.session_state.tabla = core.aplicar_masivo(
                    st.session_state.tabla, "Aprobado", True, mask=mask_g)
                persistir_tabla()
        with a2:
            if st.button("❌ Desaprobar grupo"):
                st.session_state.tabla = core.aplicar_masivo(
                    st.session_state.tabla, "Aprobado", False, mask=mask_g)
                persistir_tabla()
        with a3:
            sub_t = st.session_state.tabla[mask_g]
            st.metric(f"Aprobados ({gsel})",
                      f"{int(sub_t['Aprobado'].sum())} / {len(sub_t)}")

        # Resumen de avance por grupo
        resumen = (st.session_state.tabla
                   .groupby("GRUPO")["Aprobado"]
                   .agg(["sum", "count"]).reset_index())
        resumen["Estado"] = resumen.apply(
            lambda r: "✅ Completo" if r["sum"] == r["count"]
            else (f"⏳ {int(r['sum'])}/{int(r['count'])}"), axis=1)
        st.dataframe(
            resumen.rename(columns={"GRUPO": "Grupo", "sum": "Aprobados",
                                    "count": "Total"})[["Grupo", "Aprobados", "Total", "Estado"]],
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
        persistir_tabla()

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
                ngrupo = st.text_input("Grupo (sólo supervisor, ej. N, E, PCP, 1..5)")
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
