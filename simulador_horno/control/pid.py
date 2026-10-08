"""Controlador PID.

- ``calcular_pid`` : función pura; recibe el estado previo y devuelve el nuevo.
- ``PID``          : un controlador con su propio estado entre pasos (cada
                     simulador tiene el suyo).
"""
import math

from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import ParametrosPID
from simulador_horno.control import anti_windup as windout
from simulador_horno.control.escalado import escalar_u


def calcular_pid(error, error_prev, integral, medida, medida_prev, pid, dt):
    """Devuelve ``(u, integral, error, termino_D, termino_P)``.

    ``pid`` son las ganancias y el anti-windup (``ParametrosPID``); ``dt``
    el paso de integración en segundos.

    - integral: regla del trapecio, limitada por el anti-windup elegido
      (ver :mod:`control.anti_windup`).
    - derivada: diferencia hacia atrás de la MEDICIÓN, no del error:
      ``−(medida − medida_prev)/dt``. Con el setpoint fijo es lo mismo, pero
      evita el pico de la acción D ("derivative kick") cuando el error salta,
      como en el primer paso. Si no hay medida previa (``None``) vale 0.
    - salida ``u`` saturada por :func:`escalar_u`.
    """
    DT = dt
    if DT == 0:
        DT = 1e-6   # protección mínima

    integral_nueva = integral + 0.5 * (error + error_prev) * DT   # regla del trapecio
    derivada = 0.0 if medida_prev is None else -(medida - medida_prev) / DT
    proporcional = pid.KP * error

    u_bruta = (proporcional + pid.KI * integral_nueva + pid.KD * derivada) / limites.U_MAX
    integral = windout.limitar(pid.anti_windup, integral, integral_nueva, error, u_bruta,
                               pid.restringir_integral)

    u = proporcional + pid.KI * integral + pid.KD * derivada
    if math.isnan(u) or math.isinf(u):
        u = 0.0

    return escalar_u(u), integral, error, pid.KD * derivada, proporcional


class PID:
    """Controlador PID con estado propio.

    ``parametros`` se guarda por referencia: si la interfaz cambia una
    ganancia, el siguiente paso ya la usa.
    """

    def __init__(self, parametros=None):
        self.parametros = parametros if parametros is not None else ParametrosPID()
        self.reiniciar()

    def reiniciar(self):
        """Cada corrida empieza con el estado en cero."""
        self.error_prev = 0.0
        self.medida_prev = None   # temperatura medida en el paso anterior (derivada sobre la medición)
        self.integral = 0.0
        self.derivada = 0.0       # término derivativo ya multiplicado por KD
        self.proporcional = 0.0   # término proporcional

    def paso(self, error, medida, dt):
        """Ejecuta un paso y devuelve ``u`` en [0, 1].

        ``medida`` es la temperatura que "lee" el controlador (T_SET − error,
        es decir, incluye las perturbaciones activas).
        """
        u, self.integral, self.error_prev, self.derivada, self.proporcional = calcular_pid(
            error, self.error_prev, self.integral, medida, self.medida_prev, self.parametros, dt
        )
        self.medida_prev = medida
        return u
