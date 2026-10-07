"""Variantes de mayor orden del modelo térmico del horno.

Mismo modelo que ``modelo.horno.simular_horno`` (Euler), integrado con métodos
más precisos. Se conservan como referencia de métodos numéricos; el
simulador usa por ahora únicamente Euler.
"""
import math

from simulador_horno.configuracion import parametros_horno as var


def simular_horno_heun(T_actual, u):
    """Método de Heun (predictor-corrector, RK de 2º orden)."""
    try:
        TAU = var.TAU
        if TAU == 0:
            TAU = 1e-6   # evita división por cero
        DT = var.DT
        T_AMB = var.T_AMB
        B = var.B

        # Paso 1: pendiente inicial
        k1 = (1 / TAU) * (T_AMB - T_actual) + B * u

        # Paso 2: valor predicho
        T_pred = T_actual + DT * k1

        # Paso 3: pendiente final
        k2 = (1 / TAU) * (T_AMB - T_pred) + B * u

        # Paso 4: corrección (promedio de pendientes)
        T_nuevo = T_actual + (DT / 2) * (k1 + k2)

        if math.isnan(T_nuevo) or math.isinf(T_nuevo):
            T_nuevo = T_actual

    except Exception:
        T_nuevo = T_actual

    return T_nuevo


def simular_horno_runge(T_actual, u):
    """Método de Runge-Kutta de 4º orden."""
    try:
        TAU = var.TAU
        if TAU == 0:
            TAU = 1e-6  # evita división por cero

        h = var.DT

        def f(T, u):
            return (1 / TAU) * (var.T_AMB - T) + var.B * u

        k1 = f(T_actual, u)
        k2 = f(T_actual + 0.5 * h * k1, u)
        k3 = f(T_actual + 0.5 * h * k2, u)
        k4 = f(T_actual + h * k3, u)

        T_nuevo = T_actual + (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)

        if math.isnan(T_nuevo) or math.isinf(T_nuevo):
            T_nuevo = T_actual

    except Exception:
        T_nuevo = T_actual

    return T_nuevo
