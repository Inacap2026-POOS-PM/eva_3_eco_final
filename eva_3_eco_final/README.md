# Proyecto EcoTech – Evaluación Sumativa 3

## 1. Descripción

Este proyecto consiste en un programa desarrollado en Python que consulta información del clima y tipos de cambio mediante APIs. También permite calcular pagos internacionales, guardar información en SQLite y controlar el acceso mediante usuario y contraseña.

## 2. Estructura del proyecto

- `main.py`: Menú principal del programa.
- `src/configuracion.py`: Configuración de APIs y datos permitidos.
- `src/validacion.py`: Validación de datos ingresados.
- `src/auth.py`: Control de usuarios y contraseñas.
- `src/almacenamiento.py`: Guardado de información en SQLite.
- `src/servicios.py`: Conexión con las APIs y cálculos.
- `tests/`: Pruebas del programa.
- `documentacion/`: Análisis y justificación del uso de IA.
- `requirements.txt`: Librerías necesarias.

## 3. Cómo ejecutar el programa

1. Abrir la carpeta del proyecto en Visual Studio Code.
2. Tener instalado Python 3.12 o superior.
3. Abrir la terminal e instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

4. Ejecutar el programa:

```bash
python main.py
```

5. En el primer inicio se debe crear un usuario administrador.

Para ejecutar las pruebas:

```bash
python -m unittest discover -s tests -v
```

## 4. APIs utilizadas

- **Open-Meteo:** Obtiene información del clima.
- **ExchangeRate-API:** Obtiene los tipos de cambio entre monedas.

Ambas APIs funcionan sin necesidad de una llave de acceso.

## 5. Seguridad implementada

El programa cuenta con las siguientes medidas de seguridad:

- Contraseñas protegidas mediante hash y salt.
- Validación de los datos ingresados.
- Control de acceso según el tipo de usuario.
- Consultas SQL parametrizadas.
- Manejo de errores en las conexiones con las APIs.
- Registro de errores en un archivo de seguridad.
- Uso de `Decimal` para realizar cálculos monetarios.