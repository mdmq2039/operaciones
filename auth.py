"""
auth.py
=================
Control de acceso por supervisor para el Aplicativo de Tareo de Operaciones.

Roles:
  - coordinador : ve y aprueba TODOS los grupos, genera el reporte final y
                  administra los usuarios.
  - supervisor  : sólo ve y autoriza SU grupo.

Los usuarios se guardan en 'usuarios.json' (junto a este archivo). Las
contraseñas se almacenan con hash SHA-256 + sal, nunca en texto plano.
La primera vez se crean usuarios por defecto (uno por grupo + coordinador).
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets

RUTA_BASE = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_USUARIOS = os.path.join(RUTA_BASE, "usuarios.json")

# Grupos conocidos del tareo (se pueden ampliar desde el panel de usuarios)
GRUPOS_POR_DEFECTO = ["N", "E", "PCP", "1", "2", "3", "4", "5"]


# --------------------------------------------------------------------------- #
#  Hash de contraseñas                                                         #
# --------------------------------------------------------------------------- #
def _hash(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _nuevo_registro(password: str, rol: str, grupo) -> dict:
    salt = secrets.token_hex(8)
    return {"salt": salt, "hash": _hash(password, salt), "rol": rol, "grupo": grupo}


# --------------------------------------------------------------------------- #
#  Carga / guardado                                                            #
# --------------------------------------------------------------------------- #
def usuarios_por_defecto() -> dict:
    """Coordinador + un supervisor por grupo, con claves iniciales sencillas."""
    users = {
        "coordinador": _nuevo_registro("coord123", "coordinador", None),
    }
    for g in GRUPOS_POR_DEFECTO:
        users[f"sup_{g}".lower()] = _nuevo_registro(f"{g}123", "supervisor", g)
    return users


def cargar_usuarios() -> dict:
    if not os.path.exists(ARCHIVO_USUARIOS):
        users = usuarios_por_defecto()
        guardar_usuarios(users)
        return users
    try:
        with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        users = usuarios_por_defecto()
        guardar_usuarios(users)
        return users


def guardar_usuarios(users: dict) -> None:
    with open(ARCHIVO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


# --------------------------------------------------------------------------- #
#  Operaciones                                                                 #
# --------------------------------------------------------------------------- #
def verificar(usuario: str, password: str) -> dict | None:
    """Devuelve {usuario, rol, grupo} si las credenciales son válidas, si no None."""
    users = cargar_usuarios()
    u = (usuario or "").strip().lower()
    reg = users.get(u)
    if not reg:
        return None
    if _hash(password, reg["salt"]) == reg["hash"]:
        return {"usuario": u, "rol": reg["rol"], "grupo": reg.get("grupo")}
    return None


def crear_o_actualizar(usuario: str, password: str | None, rol: str, grupo) -> None:
    """Crea un usuario o actualiza rol/grupo (y clave si se pasa)."""
    users = cargar_usuarios()
    u = usuario.strip().lower()
    if password:
        users[u] = _nuevo_registro(password, rol, grupo)
    elif u in users:
        users[u]["rol"] = rol
        users[u]["grupo"] = grupo
    else:
        # usuario nuevo sin clave -> clave por defecto = usuario
        users[u] = _nuevo_registro(u, rol, grupo)
    guardar_usuarios(users)


def eliminar(usuario: str) -> None:
    users = cargar_usuarios()
    users.pop(usuario.strip().lower(), None)
    guardar_usuarios(users)


def cambiar_password(usuario: str, nueva: str) -> bool:
    users = cargar_usuarios()
    u = usuario.strip().lower()
    if u not in users:
        return False
    reg = users[u]
    salt = secrets.token_hex(8)
    reg["salt"] = salt
    reg["hash"] = _hash(nueva, salt)
    guardar_usuarios(users)
    return True


def listar() -> list[dict]:
    users = cargar_usuarios()
    return [{"usuario": k, "rol": v["rol"], "grupo": v.get("grupo")}
            for k, v in sorted(users.items())]
