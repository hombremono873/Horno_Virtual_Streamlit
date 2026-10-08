"""Métodos numéricos para integrar el modelo térmico del horno.

    dT/dt = (1/TAU)·(T_AMB − T) + B·u

Mismo modelo que ``modelo.horno.simular_horno`` (Euler), integrado con
métodos de mayor orden. El usuario elige el método desde el menú
(``formularios.configurar_metodo``); ``METODOS`` asocia cada clave con su
función de paso, todas con la misma firma ``(T_actual, u) -> T_nuevo``.

    Método   Orden   Evaluaciones de dT/dt por paso
    Euler      1       1
    Heun       2       2
    RK4        4       4
"""
import math

from simulador_horno.configuracion import parametros_horno as var
from simulador_horno.modelo.horno import simular_horno


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


# Clave (parametros_simulacion.metodo) -> nombre visible y función de paso.
NOMBRES = {
    "euler": "Euler",
    "heun": "Heun (RK2)",
    "rk4": "Runge-Kutta 4",
}

# Teoría de cada método: orden de convergencia y evaluaciones de dT/dt por paso.
ORDEN = {"euler": 1, "heun": 2, "rk4": 4}
EVALUACIONES = {"euler": 1, "heun": 2, "rk4": 4}

METODOS = {
    "euler": simular_horno,
    "heun": simular_horno_heun,
    "rk4": simular_horno_runge,
}
