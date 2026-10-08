"""Modelo térmico de primer orden del horno.

    dT/dt = (1/TAU)·(T_amb − T) + B·(u·potencia) + perdida_extra·(T_amb − T)

Sin perturbaciones del entorno (``ENTORNO_IDEAL``) se reduce a

    dT/dt = (1/TAU)·(T_AMB − T) + B·u

``derivada`` es la ÚNICA definición de la ecuación: la usan Euler (aquí) y
Heun / RK4 (``numerico.integradores``), así que las perturbaciones físicas
actúan igual con cualquier método.

``entorno`` describe las condiciones del paso en curso y lo fija el motor
solo mientras integra un paso con perturbaciones del horno activas:

- ``T_amb``         : temperatura ambiente efectiva (None = ``T_AMB``).
- ``perdida_extra`` : pérdidas adicionales en 1/s (puerta abierta).
- ``potencia``      : fracción de la potencia nominal que entrega la red.
"""
import math

from simulador_horno.configuracion import parametros_horno as var

ENTORNO_IDEAL = (None, 0.0, 1.0)   # (T_amb, perdida_extra, potencia)
entorno = ENTORNO_IDEAL


def derivada(T, u):
    """dT/dt con las condiciones de ``entorno``.

    Con el entorno ideal da exactamente el mismo resultado (bit a bit) que
    la fórmula sin perturbaciones: u·1.0 = u y sumar 0.0 no altera nada.
    """
    T_amb, perdida_extra, potencia = entorno
    if T_amb is None:
        T_amb = var.T_AMB
    TAU = var.TAU
    if TAU == 0:
        TAU = 1e-6   # evita división por cero
    return (1 / TAU) * (T_amb - T) + var.B * (u * potencia) + perdida_extra * (T_amb - T)


def simular_horno(T_actual, u):
    """Avanza la temperatura un paso ``DT`` con el método de Euler."""
    try:
        T_nuevo = T_actual + var.DT * derivada(T_actual, u)

        if math.isnan(T_nuevo) or math.isinf(T_nuevo):
            T_nuevo = T_actual

    except Exception:
        T_nuevo = T_actual

    return T_nuevo
