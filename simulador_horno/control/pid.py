"""Controlador PID.

- ``calcular_pid``   : función pura, no toca estado global.
- ``actualizar_pid`` : aplica un paso y persiste el estado en ``parametros_pid``.
"""
import math

from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as var_horno
from simulador_horno.configuracion import parametros_pid as var
from simulador_horno.control import anti_windup as windout
from simulador_horno.control.escalado import escalar_u


def calcular_pid(error, error_prev, integral, medida, medida_prev):
    """Devuelve ``(u, integral, error, termino_D, termino_P)``.

    - integral: regla del trapecio, limitada por el anti-windup elegido
      (``parametros_pid.anti_windup``, ver :mod:`control.anti_windup`).
    - derivada: diferencia hacia atrás de la MEDICIÓN, no del error:
      ``−(medida − medida_prev)/DT``. Con el setpoint fijo es lo mismo, pero
      evita el pico de la acción D ("derivative kick") cuando el error salta,
      como en el primer paso. Si no hay medida previa (``None``) vale 0.
    - salida ``u`` saturada por :func:`escalar_u`.
    """
    DT = var_horno.DT
    if DT == 0:
        DT = 1e-6   # protección mínima

    integral_nueva = integral + 0.5 * (error + error_prev) * DT   # regla del trapecio
    derivada = 0.0 if medida_prev is None else -(medida - medida_prev) / DT
    proporcional = var.KP * error

    u_bruta = (proporcional + var.KI * integral_nueva + var.KD * derivada) / limites.U_MAX
    integral = windout.limitar(var.anti_windup, integral, integral_nueva, error, u_bruta)

    u = proporcional + var.KI * integral + var.KD * derivada
    if math.isnan(u) or math.isinf(u):
        u = 0.0

    return escalar_u(u), integral, error, var.KD * derivada, proporcional


def actualizar_pid(error, medida):
    """Ejecuta un paso del PID y guarda el estado interno en ``parametros_pid``.

    ``medida`` es la temperatura que "lee" el controlador (T_SET − error, es
    decir, incluye las perturbaciones activas).
    """
    u, var.integral, var.error_prev, var.derivada, var.proporcional = calcular_pid(
        error, var.error_prev, var.integral, medida, var.medida_prev
    )
    var.medida_prev = medida
    return u
