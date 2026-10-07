"""Modelo térmico de primer orden del horno.

    dT/dt = (1 / TAU) * (T_AMB - T) + B * u

Integración por el método de Euler (un paso por iteración de simulación).
Las variantes Heun y Runge-Kutta 4 viven en ``numerico.integradores``.
"""
import math

from simulador_horno.configuracion import parametros_horno as var


def simular_horno(T_actual, u):
    """Avanza la temperatura un paso ``DT`` con el método de Euler."""
    try:
        TAU = var.TAU
        if TAU == 0:
            TAU = 1e-6   # evita división por cero

        dT = (1 / TAU) * (var.T_AMB - T_actual) + var.B * u
        T_nuevo = T_actual + var.DT * dT

        if math.isnan(T_nuevo) or math.isinf(T_nuevo):
            T_nuevo = T_actual

    except Exception:
        T_nuevo = T_actual

    return T_nuevo
