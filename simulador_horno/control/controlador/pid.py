"""Controlador PID.

- ``calcular_pid``   : función pura, no toca estado global.
- ``actualizar_pid`` : aplica un paso y persiste el estado en ``parametros_pid``.
"""
import math

from simulador_horno.config import limites
from simulador_horno.config import parametros_horno as var_horno
from simulador_horno.config import parametros_pid as var
from simulador_horno.control.controlador import anti_windup as windout
from simulador_horno.control.controlador.escalado import escalar_u


def calcular_pid(error, error_prev, integral):
    """Devuelve ``(u, integral, error, termino_D, termino_P)``.

    - integral: regla del trapecio.
    - derivada: diferencia hacia atrás.
    - salida ``u`` saturada por :func:`escalar_u`.
    """
    DT = var_horno.DT
    if DT == 0:
        DT = 1e-6   # protección mínima

    integral += 0.5 * (error + error_prev) * DT   # integral por regla del trapecio
    derivada = (error - error_prev) / DT

    if integral > limites.UMBRAL_INTEGRAL:
        integral = windout.minimizar_integral(integral)

    proporcional = var.KP * error
    u = proporcional + var.KI * integral + var.KD * derivada
    if math.isnan(u) or math.isinf(u):
        u = 0.0

    return escalar_u(u), integral, error, var.KD * derivada, proporcional


def actualizar_pid(error):
    """Ejecuta un paso del PID y guarda el estado interno en ``parametros_pid``."""
    u, var.integral, var.error_prev, var.derivada, var.proporcional = calcular_pid(
        error, var.error_prev, var.integral
    )
    return u
