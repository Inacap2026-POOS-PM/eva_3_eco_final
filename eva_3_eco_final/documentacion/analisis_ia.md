# Análisis crítico y ajustes del código con apoyo de IA 

**Estudiante:** [Damian Portiño]  
**Fecha:** [20/11/2026]  
**Asignatura:** TI3021 – Programación Orientada a Objeto Seguro

## 1. Herramientas de IA utilizadas

- **ChatGPT:** Utilizado para hacer consultas y resolver dudas.
- **Claude:** Utilizado para revisar y corregir el código según los requisitos.

Se solicitó mantener los cambios necesarios, sin agregar funcionalidades que no fueran solicitadas. El código generado fue revisado antes de incorporarlo.

## 2. Problemas encontrados en el código inicial

Durante la revisión se identificaron los siguientes problemas:

- Contraseñas y llaves API sin protección.
- Falta de validación de los datos ingresados.
- Conexiones con APIs sin control de tiempo de espera.
- Manejo incorrecto de errores.
- Uso de `float` para cálculos monetarios.
- Falta de control de acceso y almacenamiento de información.

Estos problemas podían afectar la seguridad y el funcionamiento del programa.

## 3. Correcciones realizadas

Para mejorar el proyecto se aplicaron los siguientes cambios:

- Se protegieron las contraseñas utilizando PBKDF2 y salt.
- Se agregó validación para ciudades, monedas y datos ingresados.
- Se incorporó control de errores en las conexiones con las APIs.
- Se agregó SQLite para guardar la información.
- Se utilizaron consultas SQL parametrizadas.
- Se implementó `Decimal` para evitar errores en cálculos monetarios.
- Se mejoró el registro de errores mediante un archivo de seguridad.
- Se agregó un cierre controlado ante interrupciones del programa.

## 4. Pruebas realizadas

Para comprobar el funcionamiento se ejecutaron los siguientes comandos:

```bash
python -m compileall -q main.py src tests
python -m unittest discover -s tests -v
```

**Resultado:** Se ejecutaron 21 pruebas y todas finalizaron correctamente (21 OK).

También se realizaron pruebas para comprobar:

- Funcionamiento sin conexión a Internet.
- Errores al consultar las APIs.
- Validación de usuarios y contraseñas.
- Guardado y lectura de información en SQLite.
- Cierre correcto del programa ante interrupciones.

**Prueba con APIs reales:**

[Completar con el resultado obtenido al consultar el clima y calcular un pago, indicando la fecha.]

## 5. Reflexión final

La inteligencia artificial ayudó a desarrollar y revisar el proyecto, pero el código no se utilizó directamente sin revisarlo.

Se realizaron correcciones para mejorar la seguridad, validar los datos y controlar los errores. Las pruebas permitieron comprobar que el programa funciona correctamente en los casos evaluados.

Finalmente, se considera que la IA fue una herramienta de apoyo para mejorar el código y comprender los cambios realizados.