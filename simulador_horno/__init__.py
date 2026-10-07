"""Simulador de calentamiento de un horno eléctrico con control PID.

Paquete organizado por capas:

- ``config``     : parámetros configurables del horno / PID y constantes fijas.
- ``control``    : lógica de control pura (planta térmica, controlador, actuador,
                   perturbaciones). No realiza entrada/salida.
- ``simulacion`` : orquestación del bucle de simulación.
- ``interfaces`` : interfaces visuales (consola rich, gráficas matplotlib, alarmas).
"""
