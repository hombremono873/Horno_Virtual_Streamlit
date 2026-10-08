"""Modelo térmico de primer orden del horno.

    dT/dt = (1/TAU)·(T_amb − T) + B·(u·potencia) + perdida_extra·(T_amb − T)

Sin perturbaciones del entorno (``ENTORNO_IDEAL``) se reduce a

    dT/dt = (1/TAU)·(T_AMB − T) + B·u

``derivada`` es la ÚNICA definición de la ecuación: la usan Euler (aquí) y
Heun / RK4 (``numerico.integradores``), así que las perturbaciones físicas
actúan igual con cualquier método.

Todo se recibe como argumento (sin estado global):

- ``horno``   : los parámetros físicos (``configuracion.parametros.ParametrosHorno``
                o cualquier objeto con ``T_AMB``, ``TAU``, ``B`` y ``DT``).
- ``entorno`` : las condiciones del paso en curso, ``(T_amb, perdida_extra, potencia)``:
    - ``T_amb``         : temperatura ambiente efectiva (None = ``horno.T_AMB``).
    - ``perdida_extra`` : pérdidas adicionales en 1/s (puerta abierta).
    - ``potencia``      : fracción de la potencia nominal que entrega la red.
"""
import math

ENTORNO_IDEAL = (None, 0.0, 1.0)   # (T_amb, perdida_extra, potencia)


def derivada(T, u, horno, entorno=ENTORNO_IDEAL):
    """dT/dt con los parámetros de ``horno`` y las condiciones de ``entorno``.

    Con el entorno ideal da exactamente el mismo resultado (bit a bit) que
    la fórmula sin perturbaciones: u·1.0 = u y sumar 0.0 no altera nada.
    """
    T_amb, perdida_extra, potencia = entorno
    if T_amb is None:
        T_amb = horno.T_AMB
    TAU = horno.TAU
    if TAU == 0:
        TAU = 1e-6   # evita división por cero
    return (1 / TAU) * (T_amb - T) + horno.B * (u * potencia) + perdida_extra * (T_amb - T)


def simular_horno(T_actual, u, horno, entorno=ENTORNO_IDEAL):
    """Avanza la temperatura un paso ``horno.DT`` con el método de Euler."""
    try:
        T_nuevo = T_actual + horno.DT * derivada(T_actual, u, horno, entorno)

        if math.isnan(T_nuevo) or math.isinf(T_nuevo):
            T_nuevo = T_actual

    except Exception:
        T_nuevo = T_actual

    return T_nuevo
