"""Capa de lógica de control (sin entrada/salida).

- ``modelo_termico`` : la planta (evolución de la temperatura del horno).
- ``controlador``    : el PID (señal de control, anti-windup, escalado).
- ``actuador``       : traducción de la señal de control a ángulo de conducción.
- ``perturbaciones`` : ruido, senoide e impulsos sobre la señal de error.
"""
