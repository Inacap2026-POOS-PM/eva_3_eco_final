"""Pruebas unitarias de validación, autenticación y consumo externo simulado."""
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from src import configuracion as cfg
from src import servicios
from src.almacenamiento import (
    conexion,
    guardar_clima,
    guardar_pago,
    historial,
    inicializar_base,
    sanitizar,
)
from src.auth import crear_usuario, verificar_credenciales
from src.validacion import (
    ValidacionError,
    validar_ciudad,
    validar_contrasena,
    validar_moneda,
    validar_monto,
    validar_usuario,
)


class PruebasBase(unittest.TestCase):
    def setUp(self):
        self._original = (cfg.DATOS_DIR, cfg.DB_PATH, cfg.LOG_PATH)
        self._temporal = tempfile.TemporaryDirectory()
        directorio = Path(self._temporal.name)
        cfg.DATOS_DIR = directorio
        cfg.DB_PATH = directorio / "prueba.db"
        cfg.LOG_PATH = directorio / "prueba.log"
        inicializar_base()

    def tearDown(self):
        cfg.DATOS_DIR, cfg.DB_PATH, cfg.LOG_PATH = self._original
        self._temporal.cleanup()


class PruebasValidacion(PruebasBase):
    def test_usuario_rechaza_caracteres_de_inyeccion(self):
        with self.assertRaises(ValidacionError):
            validar_usuario("admin' OR 1=1")

    def test_ciudad_se_normaliza_y_se_restringe_a_lista(self):
        self.assertEqual(validar_ciudad("Buenos Aires"), "buenosaires")
        with self.assertRaises(ValidacionError):
            validar_ciudad("http://servicio-interno/local")

    def test_monto_rechaza_valores_invalidos(self):
        with self.assertRaises(ValidacionError):
            validar_monto("-10")
        with self.assertRaises(ValidacionError):
            validar_monto("12.345")
        self.assertEqual(validar_monto("1500.5"), Decimal("1500.50"))

    def test_moneda_fuera_de_la_lista_se_rechaza(self):
        with self.assertRaises(ValidacionError):
            validar_moneda("XYZ")
        self.assertEqual(validar_moneda(" usd "), "USD")

    def test_contrasena_vacia_o_solo_espacios_se_rechaza(self):
        for valor in ("", "        "):
            with self.assertRaises(ValidacionError):
                validar_contrasena(valor)


class PruebasAutenticacion(PruebasBase):
    def test_contrasena_no_guarda_texto_plano_y_comparacion_es_correcta(self):
        crear_usuario("dante", "ClaveSegura123", "administrador")
        crear_usuario("dante2", "OtraClave456", "empleado")

        with conexion() as conn:
            filas = conn.execute("SELECT usuario, salt, hash FROM usuarios").fetchall()
        self.assertNotIn(b"ClaveSegura123", [bytes(fila["hash"]) for fila in filas])
        self.assertNotEqual(bytes(filas[0]["salt"]), bytes(filas[1]["salt"]))

        self.assertEqual(
            verificar_credenciales("dante", "ClaveSegura123"),
            {"usuario": "dante", "rol": "administrador"},
        )
        self.assertIsNone(verificar_credenciales("dante", "clave-incorrecta"))

    def test_login_rechaza_vacios_y_usuario_inexistente(self):
        crear_usuario("dante", "ClaveSegura123", "administrador")
        with self.assertRaises(ValidacionError):
            verificar_credenciales("", "ClaveSegura123")
        with self.assertRaises(ValidacionError):
            verificar_credenciales("dante", "")
        self.assertIsNone(verificar_credenciales("noexiste", "ClaveSegura123"))


class PruebasServicios(PruebasBase):
    def test_clima_extrae_campos_relevantes(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {
            "current": {
                "temperature_2m": 18.6,
                "relative_humidity_2m": 62,
                "weather_code": 2,
                "time": "2026-11-19T12:00",
            }
        }
        with patch("src.servicios.requests.get", return_value=respuesta) as solicitar:
            clima = servicios.consultar_clima("Santiago")
        self.assertEqual(clima["temperatura"], 18.6)
        self.assertEqual(clima["humedad"], 62)
        self.assertEqual(clima["condicion"], "Parcialmente nublado")
        self.assertEqual(solicitar.call_args.kwargs["params"]["latitude"], -33.45)
        self.assertEqual(solicitar.call_args.kwargs["timeout"], cfg.TIMEOUT_SEGUNDOS)

    def test_error_500_se_reintenta_y_luego_continua(self):
        fallida = Mock(status_code=500)
        correcta = Mock(status_code=200)
        correcta.json.return_value = {
            "current": {
                "temperature_2m": 20,
                "relative_humidity_2m": 50,
                "weather_code": 0,
            }
        }
        with patch("src.servicios.requests.get", side_effect=[fallida, correcta]), patch(
            "src.servicios.time.sleep"
        ) as dormir:
            clima = servicios.consultar_clima("Santiago")
        self.assertEqual(clima["condicion"], "Despejado")
        self.assertEqual(dormir.call_count, 1)

    def test_error_404_no_expone_url_ni_secreto(self):
        respuesta = Mock(status_code=404)
        with patch("src.servicios.requests.get", return_value=respuesta):
            with self.assertRaises(servicios.ServicioError) as contexto:
                servicios.consultar_clima("Santiago")
        mensaje = str(contexto.exception)
        self.assertNotIn("http", mensaje)
        self.assertNotIn(cfg.CLIMA_URL, mensaje)

    def test_calculo_de_pago_usa_decimal(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {
            "result": "success",
            "rates": {"CLP": "950.5"},
            "time_last_update_utc": "Thu, 19 Nov 2026 00:00:01 +0000",
        }
        with patch("src.servicios.requests.get", return_value=respuesta):
            pago = servicios.calcular_pago("100.00", "USD", "CLP")
        self.assertEqual(pago["total"], "95050.00")
        self.assertEqual(pago["monto"], "100.00")

    def test_timeout_no_detiene_el_programa(self):
        with patch("src.servicios.requests.get", side_effect=requests.exceptions.Timeout), patch(
            "src.servicios.time.sleep"
        ):
            with self.assertRaises(servicios.ServicioError) as contexto:
                servicios.consultar_clima("Santiago")
        self.assertIn("Tiempo de espera", str(contexto.exception))

    def test_error_de_conexion_se_informa_sin_detalles(self):
        error = requests.exceptions.ConnectionError("https://api.open-meteo.com?api_key=SECRETO")
        with patch("src.servicios.requests.get", side_effect=error), patch(
            "src.servicios.time.sleep"
        ):
            with self.assertRaises(servicios.ServicioError) as contexto:
                servicios.consultar_clima("Santiago")
        self.assertNotIn("SECRETO", str(contexto.exception))
        self.assertNotIn("http", str(contexto.exception))

    def test_error_500_persistente_termina_con_mensaje_controlado(self):
        with patch("src.servicios.requests.get", return_value=Mock(status_code=500)), patch(
            "src.servicios.time.sleep"
        ):
            with self.assertRaises(servicios.ServicioError):
                servicios.consultar_clima("Santiago")

    def test_json_invalido_se_controla(self):
        respuesta = Mock(status_code=200)
        respuesta.json.side_effect = ValueError("no es json")
        with patch("src.servicios.requests.get", return_value=respuesta):
            with self.assertRaises(servicios.ServicioError):
                servicios.consultar_clima("Santiago")

    def test_404_en_tipo_de_cambio_se_controla(self):
        with patch("src.servicios.requests.get", return_value=Mock(status_code=404)):
            with self.assertRaises(servicios.ServicioError):
                servicios.calcular_pago("100", "USD", "CLP")

    def test_datos_climaticos_inutilizables_se_rechazan(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {"current": {"temperature_2m": None}}
        with patch("src.servicios.requests.get", return_value=respuesta):
            with self.assertRaises(servicios.ServicioError):
                servicios.consultar_clima("Santiago")

    def test_moneda_invalida_no_llega_a_la_api(self):
        with patch("src.servicios.requests.get") as solicitar:
            with self.assertRaises(ValidacionError):
                servicios.calcular_pago("100", "USD", "http://malo")
        solicitar.assert_not_called()

    def test_llave_api_no_se_envia_a_servicios_que_no_la_requieren(self):
        respuesta = Mock(status_code=200)
        respuesta.json.return_value = {
            "current": {"temperature_2m": 20, "relative_humidity_2m": 50, "weather_code": 0}
        }
        with patch.dict(os.environ, {cfg.VARIABLE_API_KEY: "LLAVE-SECRETA"}):
            with patch("src.servicios.requests.get", return_value=respuesta) as solicitar:
                servicios.consultar_clima("Santiago")
            self.assertNotIn("X-API-Key", solicitar.call_args.kwargs["headers"])
            self.assertEqual(
                servicios._cabeceras(requiere_llave=True)["X-API-Key"], "LLAVE-SECRETA"
            )


class PruebasAlmacenamiento(PruebasBase):
    def test_clima_y_pago_se_guardan_y_se_leen_desde_la_base_local(self):
        guardar_clima(
            "dante",
            {"ciudad": "Santiago", "temperatura": 18.6, "humedad": 62, "condicion": "Despejado"},
        )
        guardar_pago(
            "dante",
            {"origen": "USD", "destino": "CLP", "monto": "100.00", "tasa": "950.5", "total": "95050.00"},
        )
        clima = historial("clima")
        pagos = historial("pagos")
        self.assertEqual(clima[0]["ciudad"], "Santiago")
        self.assertEqual(pagos[0]["monto_destino"], "95050.00")

    def test_sanitizar_oculta_urls_y_llaves(self):
        texto = sanitizar("fallo en https://api.x.com/v1?api_key=ABC123 token=XYZ")
        self.assertNotIn("ABC123", texto)
        self.assertNotIn("XYZ", texto)
        self.assertNotIn("https://", texto)


if __name__ == "__main__":
    unittest.main()
