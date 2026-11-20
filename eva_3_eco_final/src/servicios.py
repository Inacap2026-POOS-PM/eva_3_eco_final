"""Consumo de servicios externos: clima e indicadores de tipo de cambio."""
import logging
import os
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import requests

from . import configuracion as cfg
from .almacenamiento import registrar_evento
from .validacion import validar_ciudad, validar_monto, validar_moneda

logger = logging.getLogger("ecotech_es3")
logger.addHandler(logging.NullHandler())


class ServicioError(Exception):
    """Mensaje seguro para mostrar al usuario final."""


CONDICIONES = {
    0: "Despejado",
    1: "Principalmente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna intensa",
    56: "Llovizna congelante ligera",
    57: "Llovizna congelante intensa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    66: "Lluvia congelante ligera",
    67: "Lluvia congelante intensa",
    71: "Nieve ligera",
    73: "Nieve moderada",
    75: "Nieve intensa",
    77: "Granos de nieve",
    80: "Chubascos ligeros",
    81: "Chubascos moderados",
    82: "Chubascos violentos",
    85: "Chubascos de nieve ligeros",
    86: "Chubascos de nieve intensos",
    95: "Tormenta eléctrica",
    96: "Tormenta con granizo ligero",
    99: "Tormenta con granizo intenso",
}


def _cabeceras(requiere_llave=False):
    cabeceras = {"Accept": "application/json", "User-Agent": "EcoTech-ES3/1.0"}
    # La llave solo se envía a un servicio que la exige. Las APIs actuales
    # (Open-Meteo y ExchangeRate-API open access) no la necesitan.
    if requiere_llave:
        clave = os.environ.get(cfg.VARIABLE_API_KEY)
        if clave:
            cabeceras["X-API-Key"] = clave
    return cabeceras


def _solicitar(url, params, contexto, requiere_llave=False):
    for intento in range(1, cfg.MAX_REINTENTOS + 1):
        try:
            respuesta = requests.get(
                url,
                params=params,
                headers=_cabeceras(requiere_llave),
                timeout=cfg.TIMEOUT_SEGUNDOS,
            )
        except requests.exceptions.Timeout:
            registrar_evento(logger, contexto, TimeoutError("tiempo de espera agotado"))
            if intento < cfg.MAX_REINTENTOS:
                time.sleep(cfg.RETRASO_REINTENTO)
                continue
            raise ServicioError("Tiempo de espera agotado al contactar el servicio externo.") from None
        except requests.exceptions.ConnectionError:
            registrar_evento(logger, contexto, ConnectionError("sin conexión"))
            if intento < cfg.MAX_REINTENTOS:
                time.sleep(cfg.RETRASO_REINTENTO)
                continue
            raise ServicioError("No hay conexión con el servicio externo.") from None
        except requests.exceptions.RequestException as exc:
            registrar_evento(logger, contexto, exc)
            raise ServicioError("No se pudo realizar la solicitud externa.") from None

        codigo = respuesta.status_code
        if codigo == 404:
            registrar_evento(logger, contexto, LookupError("HTTP 404"))
            raise ServicioError("El servicio externo no encontró el recurso solicitado (404).")
        if 500 <= codigo <= 599:
            registrar_evento(logger, contexto, RuntimeError(f"HTTP {codigo}"))
            if intento < cfg.MAX_REINTENTOS:
                time.sleep(cfg.RETRASO_REINTENTO)
                continue
            raise ServicioError("El servicio externo no está disponible en este momento.")
        if codigo != 200:
            registrar_evento(logger, contexto, RuntimeError(f"HTTP {codigo}"))
            raise ServicioError(f"El servicio externo devolvió el estado {codigo}.")
        try:
            return respuesta.json()
        except ValueError as exc:
            registrar_evento(logger, contexto, exc)
            raise ServicioError("La respuesta del servicio no tenía formato JSON válido.") from None
    raise ServicioError("No fue posible completar la consulta externa.")


def consultar_clima(valor_ciudad):
    clave = validar_ciudad(valor_ciudad)
    ubicacion = cfg.CIUDADES[clave]
    datos = _solicitar(
        cfg.CLIMA_URL,
        {
            "latitude": ubicacion["latitud"],
            "longitude": ubicacion["longitud"],
            "current": "temperature_2m,relative_humidity_2m,weather_code",
            "timezone": "auto",
        },
        "consulta_clima",
    )
    actual = datos.get("current", {}) if isinstance(datos, dict) else {}
    temperatura = actual.get("temperature_2m")
    humedad = actual.get("relative_humidity_2m")
    codigo = actual.get("weather_code")
    if not isinstance(temperatura, (int, float)) or not isinstance(humedad, (int, float)):
        raise ServicioError("El servicio no entregó temperatura y humedad válidas.")
    return {
        "ciudad": ubicacion["nombre"],
        "temperatura": round(float(temperatura), 1),
        "humedad": int(humedad),
        "condicion": CONDICIONES.get(codigo, "Condición no catalogada"),
        "hora": str(actual.get("time", "")),
    }


def consultar_tipo_cambio(origen, destino):
    moneda_origen = validar_moneda(origen)
    moneda_destino = validar_moneda(destino)
    if moneda_origen == moneda_destino:
        raise ServicioError("Las monedas de origen y destino deben ser distintas.")
    datos = _solicitar(
        cfg.CAMBIO_URL.format(moneda=moneda_origen), {}, "consulta_tipo_cambio"
    )
    if not isinstance(datos, dict) or datos.get("result") != "success":
        raise ServicioError("El servicio de cambio no entregó una respuesta válida.")
    tasas = datos.get("rates")
    if not isinstance(tasas, dict) or moneda_destino not in tasas:
        raise ServicioError("La moneda destino no está disponible en el servicio.")
    try:
        tasa = Decimal(str(tasas[moneda_destino]))
    except InvalidOperation:
        raise ServicioError("La tasa recibida no es válida.") from None
    if not tasa.is_finite() or tasa <= 0:
        raise ServicioError("La tasa recibida no es válida.")
    return {"tasa": tasa, "fecha": str(datos.get("time_last_update_utc", ""))}


def calcular_pago(monto, origen, destino):
    monto_validado = validar_monto(monto)
    moneda_origen = validar_moneda(origen)
    moneda_destino = validar_moneda(destino)
    if moneda_origen == moneda_destino:
        raise ServicioError("Las monedas de origen y destino deben ser distintas.")
    cambio = consultar_tipo_cambio(moneda_origen, moneda_destino)
    total = (monto_validado * cambio["tasa"]).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "monto": str(monto_validado),
        "origen": moneda_origen,
        "destino": moneda_destino,
        "tasa": str(cambio["tasa"]),
        "total": str(total),
        "fecha": cambio["fecha"],
    }
