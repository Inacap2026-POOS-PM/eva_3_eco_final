"""Autenticación con contraseñas hash salteadas (PBKDF2) y comparación segura."""
import hashlib
import hmac
import secrets
import sqlite3

from . import configuracion as cfg
from .almacenamiento import conexion
from .validacion import validar_contrasena, validar_usuario


class AutenticacionError(Exception):
    """Error de autenticación destinado al usuario final."""


def derivar_hash(contrasena, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), salt, cfg.ITERACIONES_PBKDF2
    )


def crear_usuario(usuario, contrasena, rol):
    usuario = validar_usuario(usuario)
    contrasena = validar_contrasena(contrasena)
    if rol not in ("administrador", "empleado"):
        raise AutenticacionError("Rol no válido.")
    salt = secrets.token_bytes(16)
    try:
        with conexion() as conn:
            conn.execute(
                "INSERT INTO usuarios (usuario, salt, hash, rol) VALUES (?, ?, ?, ?)",
                (usuario, salt, derivar_hash(contrasena, salt), rol),
            )
    except sqlite3.IntegrityError as exc:
        raise AutenticacionError("El usuario ya existe.") from exc
    return {"usuario": usuario, "rol": rol}


def verificar_credenciales(usuario, contrasena):
    usuario = validar_usuario(usuario)
    contrasena = validar_contrasena(contrasena)
    with conexion() as conn:
        fila = conn.execute(
            "SELECT salt, hash, rol, activo FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()
    if fila is None or not fila["activo"]:
        return None
    calculado = derivar_hash(contrasena, bytes(fila["salt"]))
    if not hmac.compare_digest(calculado, bytes(fila["hash"])):
        return None
    return {"usuario": usuario, "rol": fila["rol"]}


def contar_usuarios():
    with conexion() as conn:
        return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
