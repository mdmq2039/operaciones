# -*- coding: utf-8 -*-
"""
Genera el PDF del requerimiento de integración con Murdoch Sistemas.
Ejecutar:  python generar_requerimiento_murdoch.py
Salida:    Requerimiento_Integracion_Murdoch.pdf
"""

from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

AZUL = colors.HexColor("#1F4E9B")
AZUL_OSC = colors.HexColor("#1F3864")
GRIS = colors.HexColor("#5B6770")
GRIS_CLARO = colors.HexColor("#EEF2F8")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("Tit", parent=styles["Title"], textColor=AZUL_OSC, fontSize=24,
                          leading=28, spaceAfter=6))
styles.add(ParagraphStyle("Sub", parent=styles["Normal"], textColor=GRIS, fontSize=12,
                          leading=16, alignment=TA_CENTER))
styles.add(ParagraphStyle("H1", parent=styles["Heading1"], textColor=AZUL, fontSize=15,
                          leading=19, spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle("H2", parent=styles["Heading2"], textColor=AZUL_OSC, fontSize=12.5,
                          leading=16, spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=15,
                          alignment=TA_JUSTIFY, spaceAfter=6))
styles.add(ParagraphStyle("Punto", parent=styles["Normal"], fontSize=10, leading=14))
styles.add(ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=12))
styles.add(ParagraphStyle("CellH", parent=styles["Normal"], fontSize=9, leading=12,
                          textColor=colors.white, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("Foot", parent=styles["Normal"], fontSize=8, textColor=GRIS,
                          alignment=TA_CENTER))

S = []


def P(txt, style="Body"):
    S.append(Paragraph(txt, styles[style]))


def H1(txt):
    S.append(Paragraph(txt, styles["H1"]))


def H2(txt):
    S.append(Paragraph(txt, styles["H2"]))


def SP(h=0.2):
    S.append(Spacer(1, h * cm))


def bullets(items):
    S.append(ListFlowable(
        [ListItem(Paragraph(t, styles["Punto"]), leftIndent=10) for t in items],
        bulletType="bullet", start="•", leftIndent=14, spaceAfter=6))


def tabla(data, anchos, encabezado=True):
    filas = []
    for i, row in enumerate(data):
        est = "CellH" if (encabezado and i == 0) else "Cell"
        filas.append([Paragraph(str(c), styles[est]) for c in row])
    t = Table(filas, colWidths=[a * cm for a in anchos], repeatRows=1 if encabezado else 0)
    estilo = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BFC8D6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if encabezado:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), AZUL),
                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLARO])]
    t.setStyle(TableStyle(estilo))
    S.append(t)
    SP(0.25)


# =========================================================================== #
#  PORTADA                                                                     #
# =========================================================================== #
estilo_logo = ParagraphStyle("logo", textColor=AZUL, fontSize=44, leading=50,
                             alignment=TA_CENTER, fontName="Helvetica-Bold")
estilo_tit_portada = ParagraphStyle("TitPortada", parent=styles["Title"],
                                    textColor=AZUL_OSC, fontSize=23, leading=29,
                                    spaceAfter=4, alignment=TA_CENTER)

S.append(Spacer(1, 3.2 * cm))
S.append(Paragraph("pecepe.", estilo_logo))
SP(1.0)
S.append(HRFlowable(width="45%", thickness=1.2, color=AZUL, hAlign="CENTER"))
SP(0.7)
S.append(Paragraph("Requerimiento de Integración y Desarrollo", estilo_tit_portada))
S.append(Paragraph(
    "Automatización del Tareo de Operaciones e integración vía API con el "
    "sistema de marcación <b>Murdoch Sistemas</b>", styles["Sub"]))
SP(1.6)

# Ficha de datos del documento (recuadro centrado y con etiquetas resaltadas)
ficha = [
    ["Documento", "Especificación de requerimiento para cotización (RFP)"],
    ["Dirigido a", "Murdoch Sistemas (proveedor del sistema de marcación)"],
    ["Solicitado por", "Gerencia de Operaciones — PECEPE"],
    ["Plataformas objetivo", "PC, tablet y celular (web responsiva)"],
    ["Fecha", date.today().strftime("%d/%m/%Y")],
    ["Versión", "1.0"],
]
filas_ficha = [[Paragraph(f"<b>{a}</b>", styles["Cell"]),
                Paragraph(b, styles["Cell"])] for a, b in ficha]
t_ficha = Table(filas_ficha, colWidths=[4.8 * cm, 9.2 * cm], hAlign="CENTER")
t_ficha.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (0, -1), GRIS_CLARO),
    ("TEXTCOLOR", (0, 0), (0, -1), AZUL_OSC),
    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D7DEE9")),
    ("BOX", (0, 0), (-1, -1), 0.6, AZUL),
    ("LINEAFTER", (0, 0), (0, -1), 0.6, AZUL),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
]))
S.append(t_ficha)
SP(1.2)
S.append(Paragraph("Documento confidencial — uso interno y para el proveedor",
                   ParagraphStyle("conf", parent=styles["Foot"], fontSize=8.5)))
S.append(PageBreak())

# =========================================================================== #
#  1. RESUMEN EJECUTIVO                                                        #
# =========================================================================== #
H1("1. Resumen ejecutivo")
P("PECEPE cuenta con un sistema de marcación de asistencia provisto por "
  "<b>Murdoch Sistemas</b>, del cual hoy se exporta manualmente un reporte de "
  "marcaciones (entrada/salida) que luego es procesado de forma manual en hojas "
  "de cálculo para obtener el reporte de horas de operaciones (TTHH y horas "
  "extra) que utiliza la empresa para el pago y el control del personal.")
P("Para eliminar el trabajo manual, PECEPE desarrolló internamente un aplicativo "
  "web (funcional en PC, tablet y celular) que toma el archivo de marcaciones y, "
  "mediante reglas de negocio y aprobaciones por grupo de los supervisores, "
  "genera automáticamente el reporte final de operaciones. Este documento "
  "describe ese aplicativo en detalle y solicita a Murdoch Sistemas una "
  "<b>propuesta de integración y desarrollo</b> para que esta funcionalidad "
  "quede <b>integrada dentro del propio sistema de marcación</b>, conectada por "
  "<b>API</b> directamente a su base de datos, sin exportaciones manuales.")
P("<b>Objetivo del documento:</b> que el proveedor evalúe el alcance aquí "
  "definido y entregue <b>tiempos de implementación y costos</b> para una "
  "solución personalizada, multiplataforma, con conexión por API a nuestra base "
  "de datos de reportes.")

H2("Beneficios esperados para la gerencia")
bullets([
    "Eliminación del procesamiento manual y de los errores asociados.",
    "Cálculo automático y trazable de TTHH y horas extra (25 %, 35 %, 100 %).",
    "Aprobación digital por supervisor de cada grupo, con consolidación para el coordinador.",
    "Reportes finales almacenados y consultables (histórico y entregables).",
    "Acceso seguro desde cualquier dispositivo (PC, tablet, celular).",
    "Gestión flexible de colaboradores y grupos sin depender de TI.",
])
S.append(PageBreak())

# =========================================================================== #
#  2. ALCANCE                                                                  #
# =========================================================================== #
H1("2. Objetivo y alcance del requerimiento")
P("Se requiere que Murdoch Sistemas implemente, dentro de su plataforma o como "
  "módulo integrado a ella, una solución que reproduzca y reemplace el "
  "aplicativo actual de PECEPE, cubriendo los siguientes frentes:")
bullets([
    "<b>Conexión por API a la base de datos del sistema de marcación</b> para "
    "extraer automáticamente las marcaciones requeridas (sin exportar archivos).",
    "<b>Motor de cálculo</b> de TTHH y horas extra con todas las reglas de negocio descritas.",
    "<b>Módulo de condiciones y aprobación por grupo</b>, con control de acceso por rol.",
    "<b>Generación del reporte final de operaciones</b> en pantalla y exportable a Excel.",
    "<b>Módulo de almacenamiento de reportes y entregables</b> (histórico por periodo).",
    "<b>Gestión de colaboradores y grupos</b> (alta/baja/reasignación), totalmente funcional.",
    "<b>Conexión a la base de datos de reportes de PECEPE</b> para guardar los resultados.",
    "<b>Disponibilidad multiplataforma</b> (PC, tablet y celular) mediante interfaz web responsiva.",
])

H2("Fuera de alcance (salvo que el proveedor lo proponga)")
bullets([
    "Modificación del hardware de marcación o de los relojes biométricos.",
    "Cálculo de planilla/nómina final (el entregable es el reporte de horas de operaciones).",
])
S.append(PageBreak())

# =========================================================================== #
#  3. SITUACIÓN ACTUAL                                                         #
# =========================================================================== #
H1("3. Situación actual (aplicativo de referencia de PECEPE)")
P("PECEPE ya construyó un prototipo funcional que define con precisión el "
  "comportamiento esperado. El proveedor debe tomarlo como <b>especificación de "
  "referencia</b>. Su funcionamiento es el siguiente:")

H2("Flujo de trabajo")
bullets([
    "<b>1. Carga:</b> se obtiene el reporte de marcaciones (hoy en Excel; se desea por API).",
    "<b>2. Condiciones:</b> cada supervisor revisa su grupo y aplica condiciones "
    "(corrido, jornada teórica de 12 h, refrigerio, descuento/aumento extra de horas).",
    "<b>3. Aprobación:</b> el supervisor aprueba su grupo; el coordinador ve el avance consolidado.",
    "<b>4. Reporte final:</b> se genera el REPORTE_OPERACIONES y se exporta a Excel.",
])

H2("Datos de entrada actuales (por registro de marcación)")
tabla([
    ["Campo", "Descripción", "Ejemplo"],
    ["Nombre completo", "Nombre del colaborador", "PEDRO ALVARADO VILLANUEVA"],
    ["ID", "Identificador / documento", "60773294"],
    ["Grupo", "Grupo de trabajo (N, E, PCP, 1–5, etc.)", "2"],
    ["Departamento", "Área / service", "DALUPEZ"],
    ["Fecha", "Fecha de la jornada", "25/05/2026"],
    ["Horario", "Texto del turno (día / noche)", "Planta Pecepe Lurin dia"],
    ["Hora entrada", "Marcación de entrada", "07:21"],
    ["Hora salida", "Marcación de salida", "18:05"],
    ["Horas trabajadas", "Tiempo bruto entre marcaciones", "10:44"],
], anchos=[3.5, 8.0, 4.5])
S.append(PageBreak())

# =========================================================================== #
#  4. ARQUITECTURA DE INTEGRACIÓN                                              #
# =========================================================================== #
H1("4. Arquitectura de integración propuesta")
P("El proveedor deberá conectar la solución directamente a la base de datos del "
  "sistema de marcación mediante una <b>API segura</b>, y almacenar los "
  "resultados en una <b>base de datos de reportes</b> de PECEPE. Esquema:")
bullets([
    "<b>Origen:</b> base de datos del sistema de marcación Murdoch (lectura vía API).",
    "<b>Procesamiento:</b> motor de reglas que calcula TTHH y horas extra.",
    "<b>Interfaz:</b> aplicación web responsiva (PC/tablet/celular) con login por rol.",
    "<b>Destino:</b> base de datos de reportes de PECEPE (lectura/escritura) que "
    "guarda el tareo trabajado, las aprobaciones y los reportes finales.",
])

H2("4.1 API requerida desde el sistema de marcación")
P("Se solicita a Murdoch exponer (o habilitar) servicios para obtener las "
  "marcaciones por rango de fechas y grupo. Especificación mínima esperada:")
tabla([
    ["Aspecto", "Requerimiento"],
    ["Protocolo", "API REST sobre HTTPS (JSON). Alternativa: vista/consulta directa a BD."],
    ["Autenticación", "Token (API Key / OAuth2). Credenciales gestionadas de forma segura."],
    ["Consulta principal", "Marcaciones por rango de fechas, sede y grupo."],
    ["Datos por registro", "ID, nombre, grupo, departamento/área, fecha, turno, "
                            "hora entrada, hora salida (y horas brutas si existe)."],
    ["Catálogos", "Listado de colaboradores, grupos/áreas y turnos."],
    ["Paginación", "Soporte de paginación y filtros por fecha/grupo."],
    ["Disponibilidad", "Consulta bajo demanda y/o sincronización programada."],
    ["Documentación", "Especificación de endpoints (OpenAPI/Swagger) y ambiente de pruebas."],
], anchos=[3.8, 12.2])

H2("4.2 Base de datos de reportes (destino)")
P("La solución debe persistir la información en una base de datos relacional "
  "(p. ej. PostgreSQL/SQL Server) con, al menos, las siguientes entidades:")
tabla([
    ["Entidad", "Contenido"],
    ["Colaboradores", "ID, nombre, grupo/área, estado (activo/inactivo)."],
    ["Grupos", "Código de grupo, descripción, regla de refrigerio (aplica/no aplica)."],
    ["Usuarios y roles", "Usuario, rol (coordinador/supervisor), grupo asignado, credenciales (hash)."],
    ["Tareo trabajado", "Marcaciones + condiciones por persona + TTHH + estado de aprobación."],
    ["Reportes finales", "Reporte de operaciones por periodo, con fecha, autor y archivo entregable."],
    ["Configuración", "Parámetros de reglas (minutos de refrigerio, jornadas teóricas, etc.)."],
], anchos=[3.8, 12.2])
S.append(PageBreak())

# =========================================================================== #
#  5. REGLAS DE NEGOCIO (MOTOR DE CÁLCULO)                                     #
# =========================================================================== #
H1("5. Reglas de negocio a implementar (motor de cálculo)")
P("El cálculo de las <b>TTHH</b> (Total de Horas de RR.HH.) a partir de las "
  "marcaciones debe seguir exactamente estas reglas:")

H2("5.1 Refrigerio")
bullets([
    "Por defecto se descuentan <b>45 minutos</b> de refrigerio de la jornada.",
    "<b>No se descuenta</b> refrigerio cuando el grupo está marcado como exento "
    "(actualmente: <b>E, PCP, N y 5</b>; debe ser configurable).",
    "<b>No se descuenta</b> refrigerio cuando la marcación es <b>“corrida” (C)</b>.",
])

H2("5.2 Jornada teórica de 12 horas")
bullets([
    "Si la jornada se marca como <b>“12”</b>, la TTHH es fija de <b>12 horas</b> "
    "y <b>no se aplica ningún descuento ni aumento</b>.",
    "El inicio/salida pasan a ser teóricos: día <b>07:00–19:00</b>; noche "
    "<b>19:00–07:00</b> o <b>20:00–08:00</b> (seleccionable, masivo o individual).",
])

H2("5.3 Descuento y aumento extra")
bullets([
    "<b>Descuento extra</b> (1, 2 o 3 h) y <b>Aumento extra</b> (1, 2 o 3 h) "
    "aplicables de forma masiva (a todo el grupo) o individual.",
    "Se aplican <b>adicionalmente</b>: en jornadas normales, después del "
    "descuento de refrigerio; en jornadas corridas, sobre la marcación (que no "
    "descuenta refrigerio). No aplican a la jornada teórica de 12 h.",
])

H2("5.4 Tramos de horas extra (sobre la TTHH)")
tabla([
    ["Tramo", "Definición"],
    ["Hora normal", "Hasta 8 horas."],
    ["Hora 25 %", "De 8 a 10 horas (máximo 2 horas)."],
    ["Hora 35 %", "Lo que exceda de 10 horas."],
    ["Hora 100 %", "Domingos / feriados (ingreso manual)."],
    ["Bono HH", "Ingreso manual según política de la empresa."],
], anchos=[3.5, 12.5])

H2("5.5 Ejemplos de cálculo (marcación bruta = 10:00 h)")
tabla([
    ["Caso", "Cálculo", "TTHH"],
    ["Normal (solo refrigerio)", "10 − 0.75", "9.25"],
    ["Normal + descuento 1 h", "10 − 0.75 − 1", "8.25"],
    ["Normal + aumento 2 h", "10 − 0.75 + 2", "11.25"],
    ["Corrido (sin refrigerio)", "10", "10.00"],
    ["Corrido + descuento 1 h", "10 − 1", "9.00"],
    ["Teórico 12 (ignora todo)", "fijo", "12.00"],
], anchos=[6.0, 6.0, 4.0])
S.append(PageBreak())

# =========================================================================== #
#  6. REQUISITOS FUNCIONALES                                                   #
# =========================================================================== #
H1("6. Requisitos funcionales detallados")

H2("6.1 Roles y control de acceso")
bullets([
    "<b>Coordinador de Operaciones:</b> ve y aprueba todos los grupos, genera el "
    "reporte final, administra usuarios, grupos y colaboradores.",
    "<b>Supervisor de grupo:</b> ve y autoriza únicamente su grupo asignado.",
    "Acceso con usuario y contraseña; contraseñas almacenadas cifradas.",
    "Botón de salida/cierre de sesión.",
])

H2("6.2 Módulo de condiciones (por grupo)")
bullets([
    "Acciones masivas e individuales: corrido (C), teórico 12 h, refrigerio, "
    "descuento extra, aumento extra, selección de jornada nocturna (19–07 / 20–08).",
    "Recalculo de TTHH en tiempo real al cambiar cualquier condición.",
    "Vista de marcaciones con fecha y horas en formato hh:mm.",
])

H2("6.3 Módulo de aprobación")
bullets([
    "Aprobación por grupo (masiva o individual) por parte del supervisor.",
    "Tablero de avance por grupo (aprobados / pendientes) para el coordinador.",
    "Solo los registros aprobados pasan al reporte final.",
])

H2("6.4 Reporte final de operaciones")
bullets([
    "Generación del REPORTE_OPERACIONES con las columnas y el formato corporativo.",
    "Exportación a Excel (y opcionalmente PDF/CSV).",
    "Columnas: Nombre, Producto, Turno, Zona, Área, Service, Fecha, Inicio, "
    "Corrido, Salida, Comió, Horas trabajadas, Horas total, Hora normal, "
    "Hora 25, Hora 35, Hora 100, Bono HH.",
])

H2("6.5 Módulo de almacenamiento de reportes y entregables (NUEVO)")
bullets([
    "Guardar cada reporte final por periodo (fecha, turno, grupo, autor).",
    "Histórico consultable y descargable de reportes y entregables.",
    "Control de versiones del reporte (quién generó/aprobó y cuándo).",
    "Exportación del entregable consolidado para la gerencia.",
])

H2("6.6 Gestión de colaboradores y grupos (NUEVO / funcional)")
bullets([
    "Alta, baja y edición de colaboradores.",
    "<b>Agregar colaboradores a un grupo</b> de forma sencilla y funcional, "
    "incluyendo reasignación entre grupos.",
    "Mantenimiento de grupos (crear, editar, definir si descuenta refrigerio).",
    "Asignación de supervisores a grupos.",
])
S.append(PageBreak())

# =========================================================================== #
#  7. REQUISITOS NO FUNCIONALES                                               #
# =========================================================================== #
H1("7. Requisitos técnicos y no funcionales")
tabla([
    ["Aspecto", "Requerimiento"],
    ["Multiplataforma", "Web responsiva: uso fluido en PC, tablet y celular."],
    ["Seguridad", "HTTPS/SSL, autenticación por usuario, contraseñas cifradas, "
                  "roles y permisos por grupo, registro de auditoría."],
    ["Disponibilidad", "Servicio en línea con respaldo de base de datos."],
    ["Rendimiento", "Procesamiento ágil de cientos de registros por jornada."],
    ["Concurrencia", "Varios supervisores trabajando a la vez sin pisar datos de otros grupos."],
    ["Integración", "API con el sistema de marcación y con la base de datos de reportes."],
    ["Idioma", "Español."],
    ["Capacitación", "Manual de uso y capacitación a coordinador y supervisores."],
    ["Soporte", "Garantía post-implementación y soporte (a cotizar por el proveedor)."],
], anchos=[3.8, 12.2])

H1("8. Entregables esperados del proveedor")
bullets([
    "Aplicación integrada al sistema de marcación, multiplataforma.",
    "Documentación de la API y del modelo de datos.",
    "Manual de usuario y manual técnico.",
    "Plan de pruebas y acta de aceptación.",
    "Capacitación y soporte/garantía.",
    "Código fuente o acceso según modalidad acordada.",
])
S.append(PageBreak())

# =========================================================================== #
#  9. INFORMACIÓN SOLICITADA AL PROVEEDOR (COTIZACIÓN)                         #
# =========================================================================== #
H1("9. Información que solicitamos al proveedor")
P("Para que la gerencia evalúe la propuesta, Murdoch Sistemas debe completar la "
  "siguiente información. <b>Los importes y plazos los define el proveedor.</b>")

H2("9.1 Cuadro de costos (a completar por el proveedor)")
tabla([
    ["Concepto", "Detalle", "Costo (S/. o US$)"],
    ["Análisis y diseño", "Levantamiento y especificación técnica", ""],
    ["Desarrollo de API / integración", "Conexión a la BD de marcación", ""],
    ["Motor de cálculo y módulos", "Condiciones, aprobación, reportes", ""],
    ["Módulo de almacenamiento", "Histórico de reportes y entregables", ""],
    ["Gestión de colaboradores/grupos", "Altas, bajas, reasignación", ""],
    ["Base de datos de reportes", "Implementación y migración", ""],
    ["Pruebas y puesta en marcha", "QA, despliegue, capacitación", ""],
    ["Licenciamiento / hosting", "Modalidad y periodicidad", ""],
    ["Soporte y garantía", "Mensual / anual", ""],
    ["TOTAL", "", ""],
], anchos=[5.0, 7.0, 4.0])

H2("9.2 Cronograma (a completar por el proveedor)")
tabla([
    ["Fase", "Descripción", "Duración estimada"],
    ["1. Análisis y diseño", "Especificación y diseño técnico", ""],
    ["2. Integración API", "Conexión a la BD de marcación", ""],
    ["3. Desarrollo", "Motor, módulos e interfaz", ""],
    ["4. Pruebas", "QA y validación con datos reales", ""],
    ["5. Capacitación y go-live", "Despliegue y puesta en producción", ""],
    ["Plazo total estimado", "", ""],
], anchos=[4.0, 8.0, 4.0])

H2("9.3 Condiciones a precisar")
bullets([
    "Modalidad: desarrollo a medida, módulo dentro del sistema, o SaaS.",
    "Forma de pago y cronograma de desembolsos.",
    "Tiempo de garantía y alcance del soporte.",
    "Requisitos de infraestructura (servidores, BD, hosting).",
    "Supuestos y exclusiones de la propuesta.",
])

SP(0.4)
S.append(HRFlowable(width="100%", thickness=0.6, color=AZUL))
SP(0.3)
P("<b>Nota referencial (no vinculante):</b> a modo de orden de magnitud para la "
  "planificación interna, un desarrollo de este alcance suele ubicarse en un "
  "rango de <b>6 a 12 semanas</b> de implementación. El proveedor debe confirmar "
  "tiempos y costos reales según su evaluación.", "Body")

S.append(PageBreak())

# =========================================================================== #
#  10. CRITERIOS DE ACEPTACIÓN                                                 #
# =========================================================================== #
H1("10. Criterios de aceptación")
bullets([
    "Los cálculos de TTHH y horas extra coinciden con la especificación (sección 5).",
    "La extracción por API entrega los datos correctos por fecha y grupo.",
    "El flujo completo (carga → condiciones → aprobación → reporte → guardado) funciona.",
    "Los reportes finales se almacenan y se pueden recuperar y exportar.",
    "La gestión de colaboradores y grupos opera correctamente.",
    "La solución funciona en PC, tablet y celular.",
    "Se cumplen los requisitos de seguridad y control de acceso.",
])

H1("11. Contacto")
tabla([
    ["Empresa", "PECEPE"],
    ["Área solicitante", "Gerencia de Operaciones"],
    ["Aplicación de referencia", "Tareo de Operaciones (prototipo funcional disponible)"],
    ["Responsable del requerimiento", "____________________________"],
    ["Correo / teléfono", "____________________________"],
], anchos=[5.0, 11.0], encabezado=False)

SP(0.6)
P("Este documento describe el <b>qué</b> se necesita; el <b>cómo</b> (tecnología, "
  "arquitectura final y estimaciones) corresponde a la propuesta del proveedor. "
  "Quedamos atentos a su evaluación, tiempos y costos de implementación.", "Body")


# =========================================================================== #
#  Pie de página y numeración                                                  #
# =========================================================================== #
def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#E6E9EE"))
    canvas.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.0 * cm, "PECEPE — Requerimiento de integración con Murdoch Sistemas")
    canvas.drawRightString(A4[0] - 2 * cm, 1.0 * cm, "Página %d" % doc.page)
    canvas.drawCentredString(A4[0] / 2, 0.62 * cm, "© APLICACIONES — DONET 2026")
    canvas.restoreState()


doc = SimpleDocTemplate(
    "Requerimiento_Integracion_Murdoch.pdf", pagesize=A4,
    leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    title="Requerimiento de Integración - Murdoch Sistemas", author="PECEPE")
doc.build(S, onFirstPage=_footer, onLaterPages=_footer)
print("PDF generado: Requerimiento_Integracion_Murdoch.pdf")
