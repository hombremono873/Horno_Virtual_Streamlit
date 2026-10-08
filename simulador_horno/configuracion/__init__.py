"""Configuración del simulador.

- ``parametros`` : dataclasses con lo que el usuario edita (horno, PID,
                   perturbaciones, velocidad/método) agrupadas en ``Configuracion``.
                   Cada simulador tiene la suya: no hay estado global.
- ``limites``    : constantes fijas del simulador (no editables por el usuario).
"""
