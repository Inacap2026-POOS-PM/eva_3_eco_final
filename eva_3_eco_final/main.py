"""Punto de entrada de la extensión ES3 del sistema EcoTech Solutions."""
from getpass import getpass

from src import configuracion as cfg
from src.almacenamiento import (
    configurar_logger,
    guardar_clima,
    guardar_pago,
    historial,
    inicializar_base,
    registrar_evento,
)
from src.auth import AutenticacionError, contar_usuarios, crear_usuario, verificar_credenciales
from src.servicios import ServicioError, calcular_pago, consultar_clima
from src.validacion import ValidacionError

logger = configurar_logger()


def configurar_inicio():
    inicializar_base()
    if contar_usuarios() == 0:
        print("=== Configuración inicial ===")
        print("No existen usuarios. Crea la cuenta administradora.")
        while True:
            try:
                crear_usuario(input("Usuario: "), getpass("Contraseña: "), "administrador")
                print("Cuenta creada. Ya puedes iniciar sesión.")
                return
            except (ValidacionError, AutenticacionError) as exc:
                print(f"Dato inválido: {exc}")


def iniciar_sesion():
    for _ in range(3):
        try:
            sesion = verificar_credenciales(input("Usuario: "), getpass("Contraseña: "))
        except ValidacionError as exc:
            print(f"Dato inválido: {exc}")
            continue
        if sesion:
            print(f"Bienvenido/a, {sesion['usuario']} ({sesion['rol']}).")
            return sesion
        print("Credenciales incorrectas.")
    print("Se agotaron los intentos de inicio de sesión.")
    return None


def menu_clima(sesion):
    opciones = ", ".join(item["nombre"] for item in cfg.CIUDADES.values())
    ciudad = input(f"Ciudad ({opciones}): ")
    clima = consultar_clima(ciudad)
    guardar_clima(sesion["usuario"], clima)
    print(
        f"\nClima en {clima['ciudad']}: {clima['temperatura']} °C, "
        f"{clima['condicion']}, humedad {clima['humedad']}%."
    )
    print(f"Hora local informada por la API: {clima['hora'] or 'no disponible'}")


def menu_pagos(sesion):
    monto = input("Monto a pagar: ")
    origen = input("Moneda origen (USD, EUR, CLP...): ")
    destino = input("Moneda destino (CLP, USD, EUR...): ")
    pago = calcular_pago(monto, origen, destino)
    guardar_pago(sesion["usuario"], pago)
    print(
        f"\n{pago['monto']} {pago['origen']} = {pago['total']} {pago['destino']} "
        f"(tasa: {pago['tasa']})."
    )
    print(f"Última actualización de la tasa: {pago['fecha'] or 'no informada'}")


def menu_historial():
    print("\n--- Últimas consultas de clima ---")
    filas = historial("clima")
    if not filas:
        print("Sin registros.")
    for fila in filas:
        print(
            f"{fila['registrado_en']} | {fila['ciudad']} | {fila['temperatura']} °C | "
            f"{fila['condicion']}"
        )
    print("\n--- Últimos pagos calculados ---")
    filas = historial("pagos")
    if not filas:
        print("Sin registros.")
    for fila in filas:
        print(
            f"{fila['registrado_en']} | {fila['monto_origen']} {fila['moneda_origen']} -> "
            f"{fila['monto_destino']} {fila['moneda_destino']}"
        )


def menu_crear_usuario(sesion):
    if sesion["rol"] != "administrador":
        print("Acceso denegado: esta opción requiere rol administrador.")
        return
    usuario = input("Nuevo usuario: ")
    contrasena = getpass("Contraseña: ")
    rol = input("Rol (administrador/empleado): ")
    crear_usuario(usuario, contrasena, rol)
    print("Usuario creado correctamente.")


def ejecutar():
    configurar_inicio()
    print("\nEcoTech Solutions | Extensión ES3 - Consumo seguro de APIs")
    sesion = None
    while True:
        try:
            if sesion is None:
                print("\n1) Iniciar sesión\n2) Salir")
                opcion = input("Opción: ").strip()
                if opcion == "1":
                    sesion = iniciar_sesion()
                elif opcion == "2":
                    print("Hasta luego.")
                    break
                else:
                    print("Opción no válida.")
                continue

            print(
                "\n1) Consultar clima\n2) Calcular pago internacional\n3) Ver historial local\n"
                "4) Crear usuario (administrador)\n5) Cerrar sesión\n6) Salir"
            )
            opcion = input("Opción: ").strip()
            if opcion == "1":
                menu_clima(sesion)
            elif opcion == "2":
                menu_pagos(sesion)
            elif opcion == "3":
                menu_historial()
            elif opcion == "4":
                menu_crear_usuario(sesion)
            elif opcion == "5":
                print("Sesión cerrada.")
                sesion = None
            elif opcion == "6":
                print("Hasta luego.")
                break
            else:
                print("Opción no válida.")
        except (KeyboardInterrupt, EOFError):
            raise  # se atiende en main(): salida ordenada (evita un bucle sin fin)
        except (ValidacionError, AutenticacionError, ServicioError) as exc:
            print(f"No se pudo completar la operación: {exc}")
        except Exception as exc:
            registrar_evento(logger, "error inesperado en menú", exc)
            print("Ocurrió un error interno. El sistema continúa; revise datos/seguridad.log.")


def main():
    try:
        ejecutar()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C o Ctrl+D: salida ordenada, sin traceback.
        print("\nEntrada cancelada. Hasta luego.")
    except Exception as exc:
        # Fallo al iniciar (por ejemplo, base de datos dañada): no se muestra el detalle.
        registrar_evento(logger, "error crítico en el sistema", exc)
        print("No fue posible continuar. Revise datos/seguridad.log.")


if __name__ == "__main__":
    main()
