"""Persistencia local en SQLite y registro de eventos con mensajes saneados."""
import logging
import re
import sqlite3
from contextlib import contextmanager

from . import configuracion as cfg

_SECRETO_EN_TEXTO = re.compile(r"(?i)(api[_-]?key|token|password|clave|secret)=[^&\s]+")
_URL = re.compile(r"https?://\S+")


@contextmanager
def conexion():
    cfg.DATOS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar_base():
    with conexion() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                salt BLOB NOT NULL,
                hash BLOB NOT NULL,
                rol TEXT NOT NULL CHECK (rol IN ('administrador', 'empleado')),
                activo INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS consultas_clima (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                ciudad TEXT NOT NULL,
                temperatura REAL NOT NULL,
                humedad INTEGER NOT NULL,
                condicion TEXT NOT NULL,
                registrado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                moneda_origen TEXT NOT NULL,
                moneda_destino TEXT NOT NULL,
                monto_origen TEXT NOT NULL,
                tasa TEXT NOT NULL,
                monto_destino TEXT NOT NULL,
                registrado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


def configurar_logger():
    cfg.DATOS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ecotech_es3")
    logger.setLevel(logging.INFO)
    if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        manejador = logging.FileHandler(cfg.LOG_PATH, encoding="utf-8")
        manejador.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(manejador)
    return logger


def sanitizar(mensaje):
    texto = _URL.sub("<url>", str(mensaje))
    return _SECRETO_EN_TEXTO.sub(r"\1=***", texto)


def registrar_evento(logger, contexto, exc):
    logger.error("%s | %s | %s", contexto, type(exc).__name__, sanitizar(exc))


def guardar_clima(usuario, clima):
    with conexion() as conn:
        conn.execute(
            """INSERT INTO consultas_clima
               (usuario, ciudad, temperatura, humedad, condicion)
               VALUES (?, ?, ?, ?, ?)""",
            (usuario, clima["ciudad"], clima["temperatura"], clima["humedad"], clima["condicion"]),
        )


def guardar_pago(usuario, pago):
    with conexion() as conn:
        conn.execute(
            """INSERT INTO pagos
               (usuario, moneda_origen, moneda_destino, monto_origen, tasa, monto_destino)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                usuario,
                pago["origen"],
                pago["destino"],
                pago["monto"],
                pago["tasa"],
                pago["total"],
            ),
        )


def historial(tipo, limite=5):
    consultas = {
        "clima": """SELECT ciudad, temperatura, humedad, condicion, registrado_en
                    FROM consultas_clima ORDER BY id DESC LIMIT ?""",
        "pagos": """SELECT moneda_origen, moneda_destino, monto_origen, tasa,
                           monto_destino, registrado_en
                    FROM pagos ORDER BY id DESC LIMIT ?""",
    }
    if tipo not in consultas:
        raise ValueError("Tipo de historial no reconocido.")
    with conexion() as conn:
        return conn.execute(consultas[tipo], (limite,)).fetchall()
