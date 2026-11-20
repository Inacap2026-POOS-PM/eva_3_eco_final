"""Parámetros centralizados de la extensión ES3 (sin secretos en el código)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATOS_DIR = BASE_DIR / "datos"
DB_PATH = DATOS_DIR / "ecotech_seguro.db"
LOG_PATH = DATOS_DIR / "seguridad.log"

CLIMA_URL = "https://api.open-meteo.com/v1/forecast"
CAMBIO_URL = "https://open.er-api.com/v6/latest/{moneda}"

TIMEOUT_SEGUNDOS = 8
MAX_REINTENTOS = 2
RETRASO_REINTENTO = 1.0

VARIABLE_API_KEY = "ECOTECH_API_KEY"

CIUDADES = {
    "santiago": {"nombre": "Santiago", "latitud": -33.45, "longitud": -70.67},
    "valparaiso": {"nombre": "Valparaíso", "latitud": -33.05, "longitud": -71.62},
    "concepcion": {"nombre": "Concepción", "latitud": -36.83, "longitud": -73.05},
    "lima": {"nombre": "Lima", "latitud": -12.05, "longitud": -77.04},
    "bogota": {"nombre": "Bogotá", "latitud": 4.71, "longitud": -74.07},
    "buenosaires": {"nombre": "Buenos Aires", "latitud": -34.60, "longitud": -58.38},
    "ciudaddemexico": {"nombre": "Ciudad de México", "latitud": 19.43, "longitud": -99.13},
    "madrid": {"nombre": "Madrid", "latitud": 40.42, "longitud": -3.70},
}

MONEDAS = frozenset({"CLP", "USD", "EUR", "ARS", "COP", "PEN", "MXN", "BRL"})

LONGITUD_USUARIO_MINIMA = 4
LONGITUD_USUARIO_MAXIMA = 30
LONGITUD_CONTRASENA_MINIMA = 8
ITERACIONES_PBKDF2 = 210_000
