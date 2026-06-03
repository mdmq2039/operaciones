"""
db.py
=================
Capa de base de datos (Supabase / PostgreSQL) del Aplicativo de Tareo.

Modo dual: si existe la variable de entorno DATABASE_URL se usa Postgres
(estado central compartido para Render y multi-supervisor). Si no existe,
`enabled()` devuelve False y la aplicación usa el almacenamiento local en
archivos (pickle/json) como respaldo offline.

Tablas:
  - usuarios(usuario PK, salt, hash, rol, grupo)
  - config(id PK=1, data jsonb)
  - tareo(id serial PK, ... columnas de la tabla de trabajo ..., aprobado)

Seguridad: la contraseña jamás se escribe en el código; se lee de DATABASE_URL
(definida en .env local o en variables de entorno de Render).
"""

from __future__ import annotations

import json
import os
from typing import Optional

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()  # carga .env en local (en Render las vars ya están en el entorno)
except Exception:
    pass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_ENGINE: Optional[Engine] = None

# Columnas editables del tareo (las que actualiza cada supervisor)
COLS_EDITABLES = ["corrido", "teorico12", "refrigerio", "descuento_extra",
                  "jornada_noche", "aprobado"]
# Todas las columnas persistidas del tareo (orden de insert)
COLS_TAREO = ["nombres", "grupo", "service", "fecha", "turno", "entrada",
              "salida", "horas_marcacion", "corrido", "teorico12", "refrigerio",
              "descuento_extra", "jornada_noche", "observacion", "aprobado"]


def database_url() -> Optional[str]:
    return os.environ.get("DATABASE_URL")


def enabled() -> bool:
    return bool(database_url())


def get_engine() -> Engine:
    """Engine perezoso. NullPool + SSL: compatible con el pooler de Supabase."""
    global _ENGINE
    if _ENGINE is None:
        from sqlalchemy.pool import NullPool
        url = database_url()
        if not url:
            raise RuntimeError("DATABASE_URL no está definida.")
        _ENGINE = create_engine(
            url,
            poolclass=NullPool,
            connect_args={"sslmode": "require"},
            future=True,
        )
    return _ENGINE


# --------------------------------------------------------------------------- #
#  Esquema                                                                     #
# --------------------------------------------------------------------------- #
def init_schema() -> None:
    """Crea las tablas si no existen (idempotente)."""
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            salt    TEXT NOT NULL,
            hash    TEXT NOT NULL,
            rol     TEXT NOT NULL,
            grupo   TEXT
        )""",
        """
        CREATE TABLE IF NOT EXISTS config (
            id   INTEGER PRIMARY KEY DEFAULT 1,
            data JSONB NOT NULL
        )""",
        """
        CREATE TABLE IF NOT EXISTS tareo (
            id              SERIAL PRIMARY KEY,
            nombres         TEXT,
            grupo           TEXT,
            service         TEXT,
            fecha           DATE,
            turno           TEXT,
            entrada         TEXT,
            salida          TEXT,
            horas_marcacion DOUBLE PRECISION,
            corrido         BOOLEAN,
            teorico12       BOOLEAN,
            refrigerio      BOOLEAN,
            descuento_extra DOUBLE PRECISION,
            jornada_noche   TEXT,
            observacion     TEXT,
            aprobado        BOOLEAN
        )""",
    ]
    eng = get_engine()
    with eng.begin() as cx:
        for stmt in ddl:
            cx.execute(text(stmt))


# --------------------------------------------------------------------------- #
#  Usuarios                                                                    #
# --------------------------------------------------------------------------- #
def users_load() -> dict:
    eng = get_engine()
    with eng.connect() as cx:
        rows = cx.execute(text(
            "SELECT usuario, salt, hash, rol, grupo FROM usuarios")).mappings().all()
    return {r["usuario"]: {"salt": r["salt"], "hash": r["hash"],
                           "rol": r["rol"], "grupo": r["grupo"]} for r in rows}


def users_save(users: dict) -> None:
    """Reemplaza por completo la tabla de usuarios (upsert masivo)."""
    eng = get_engine()
    with eng.begin() as cx:
        cx.execute(text("DELETE FROM usuarios"))
        for usuario, reg in users.items():
            cx.execute(text(
                "INSERT INTO usuarios (usuario, salt, hash, rol, grupo) "
                "VALUES (:u, :s, :h, :r, :g)"),
                {"u": usuario, "s": reg["salt"], "h": reg["hash"],
                 "r": reg["rol"], "g": reg.get("grupo")})


# --------------------------------------------------------------------------- #
#  Config                                                                      #
# --------------------------------------------------------------------------- #
def config_load() -> Optional[dict]:
    eng = get_engine()
    with eng.connect() as cx:
        row = cx.execute(text("SELECT data FROM config WHERE id = 1")).first()
    if not row:
        return None
    data = row[0]
    return data if isinstance(data, dict) else json.loads(data)


def config_save(data: dict) -> None:
    eng = get_engine()
    payload = json.dumps(data, ensure_ascii=False)
    with eng.begin() as cx:
        cx.execute(text(
            "INSERT INTO config (id, data) VALUES (1, CAST(:d AS JSONB)) "
            "ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data"),
            {"d": payload})


# --------------------------------------------------------------------------- #
#  Tareo (estado de trabajo compartido)                                        #
# --------------------------------------------------------------------------- #
def _df_a_filas(df: pd.DataFrame) -> list[dict]:
    filas = []
    for _, r in df.iterrows():
        fecha = r.get("FECHA")
        if pd.isna(fecha):
            fecha = None
        elif hasattr(fecha, "date"):
            fecha = fecha.date() if hasattr(fecha, "hour") else fecha
        filas.append({
            "nombres": r.get("NOMBRES"),
            "grupo": str(r.get("GRUPO")),
            "service": r.get("SERVICE"),
            "fecha": fecha,
            "turno": r.get("TURNO"),
            "entrada": r.get("ENTRADA"),
            "salida": r.get("SALIDA"),
            "horas_marcacion": float(r.get("HORAS_MARCACION") or 0.0),
            "corrido": bool(r.get("Corrido")),
            "teorico12": bool(r.get("Teorico12")),
            "refrigerio": bool(r.get("Refrigerio")),
            "descuento_extra": float(r.get("DescuentoExtra") or 0.0),
            "jornada_noche": r.get("JornadaNoche"),
            "observacion": r.get("OBSERVACION"),
            "aprobado": bool(r.get("Aprobado")),
        })
    return filas


def tareo_truncate() -> None:
    """Vacía el tareo (botón Reiniciar del coordinador)."""
    eng = get_engine()
    with eng.begin() as cx:
        cx.execute(text("TRUNCATE TABLE tareo RESTART IDENTITY"))


def tareo_replace(df: pd.DataFrame) -> None:
    """Reemplaza todo el tareo (uso exclusivo del coordinador al 'Procesar')."""
    eng = get_engine()
    filas = _df_a_filas(df)
    cols = ", ".join(COLS_TAREO)
    binds = ", ".join(f":{c}" for c in COLS_TAREO)
    with eng.begin() as cx:
        cx.execute(text("TRUNCATE TABLE tareo RESTART IDENTITY"))
        if filas:
            cx.execute(text(f"INSERT INTO tareo ({cols}) VALUES ({binds})"), filas)


# Mapeo columna DB -> columna del DataFrame de trabajo
_DB_A_DF = {
    "id": "id", "nombres": "NOMBRES", "grupo": "GRUPO", "service": "SERVICE",
    "fecha": "FECHA", "turno": "TURNO", "entrada": "ENTRADA", "salida": "SALIDA",
    "horas_marcacion": "HORAS_MARCACION", "corrido": "Corrido",
    "teorico12": "Teorico12", "refrigerio": "Refrigerio",
    "descuento_extra": "DescuentoExtra", "jornada_noche": "JornadaNoche",
    "observacion": "OBSERVACION", "aprobado": "Aprobado",
}


def tareo_load() -> Optional[pd.DataFrame]:
    """Carga el tareo desde la DB con índice = id. None si no hay datos."""
    eng = get_engine()
    with eng.connect() as cx:
        existe = cx.execute(text("SELECT COUNT(*) FROM tareo")).scalar()
        if not existe:
            return None
        df = pd.read_sql(text("SELECT * FROM tareo ORDER BY id"), cx)
    df = df.rename(columns=_DB_A_DF)
    df["GRUPO"] = df["GRUPO"].astype(str)
    df = df.set_index("id", drop=False)
    df.index.name = None
    return df


def tareo_save_subset(df_subset: pd.DataFrame) -> None:
    """Actualiza SOLO las columnas editables de las filas (por id) del grupo.

    Evita pisar el trabajo de otros supervisores que editan otros grupos.
    """
    if df_subset is None or len(df_subset) == 0:
        return
    eng = get_engine()
    sets = ", ".join(f"{c} = :{c}" for c in COLS_EDITABLES)
    params = []
    for idx, r in df_subset.iterrows():
        params.append({
            "id": int(r["id"]) if "id" in r else int(idx),
            "corrido": bool(r.get("Corrido")),
            "teorico12": bool(r.get("Teorico12")),
            "refrigerio": bool(r.get("Refrigerio")),
            "descuento_extra": float(r.get("DescuentoExtra") or 0.0),
            "jornada_noche": r.get("JornadaNoche"),
            "aprobado": bool(r.get("Aprobado")),
        })
    with eng.begin() as cx:
        cx.execute(text(f"UPDATE tareo SET {sets} WHERE id = :id"), params)
