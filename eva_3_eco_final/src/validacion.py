"""Validación de entradas: reduzca datos inválidos antes de usar APIs o Base de Datos."""
import re
from decimal import Decimal, InvalidOperation

from . import configuracion as cfg


class ValidacionError(ValueError):
    """Error de entrada destinado al usuario final."""


_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def texto_seguro(valor, campo, max_longitud=60):
    if not isinstance(valor, str):
        raise ValidacionError(f"{campo} debe ser texto.")
    texto = valor.strip()
    if not texto:
        raise ValidacionError(f"{campo} no puede estar vacío.")
    if len(texto) > max_longitud:
        raise ValidacionError(f"{campo} excede {max_longitud} caracteres.")
    if _CONTROL.search(texto):
        raise ValidacionError(f"{campo} contiene caracteres no permitidos.")
    return texto


def validar_usuario(valor):
    usuario = texto_seguro(valor, "Usuario", cfg.LONGITUD_USUARIO_MAXIMA)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", usuario):
        raise ValidacionError("Usuario: solo letras, números, punto, guión o guión bajo.")
    if len(usuario) < cfg.LONGITUD_USUARIO_MINIMA:
        raise ValidacionError("Usuario: mínimo 4 caracteres.")
    return usuario.lower()


def validar_contrasena(valor):
    if not isinstance(valor, str) or not valor.strip():
        raise ValidacionError("Contraseña no puede estar vacía.")
    if len(valor) < cfg.LONGITUD_CONTRASENA_MINIMA:
        raise ValidacionError("Contraseña: mínimo 8 caracteres.")
    if _CONTROL.search(valor):
        raise ValidacionError("Contraseña contiene caracteres no permitidos.")
    return valor


def validar_ciudad(valor):
    texto = texto_seguro(valor, "Ciudad", 40)
    clave = re.sub(r"[\s\-_]+", "", texto).lower()
    if clave not in cfg.CIUDADES:
        opciones = ", ".join(item["nombre"] for item in cfg.CIUDADES.values())
        raise ValidacionError(f"Ciudad no autorizada. Opciones: {opciones}.")
    return clave


def validar_moneda(valor):
    moneda = texto_seguro(valor, "Moneda", 3).upper()
    if moneda not in cfg.MONEDAS:
        raise ValidacionError("Moneda no autorizada. Use CLP, USD, EUR, ARS, COP, PEN, MXN o BRL.")
    return moneda


def validar_monto(valor):
    texto = texto_seguro(valor, "Monto", 18)
    try:
        monto = Decimal(texto)
    except InvalidOperation as exc:
        raise ValidacionError("Monto debe ser un número válido.") from exc
    if not monto.is_finite() or monto <= 0:
        raise ValidacionError("Monto debe ser mayor a cero.")
    if -monto.as_tuple().exponent > 2:
        raise ValidacionError("Monto admite máximo 2 decimales.")
    if monto > Decimal("1000000000"):
        raise ValidacionError("Monto excede el límite permitido.")
    return monto.quantize(Decimal("0.01"))
