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


def calcular_pid(error, error_prev, integral, medida, medida_prev, pid, dt, cortada=False):
    """Devuelve ``(u, integral, error, termino_D, termino_P)``.

    ``pid`` son las ganancias y el anti-windup (``ParametrosPID``); ``dt``
    el paso de integración en segundos.

    - integral: regla del trapecio, limitada por el anti-windup elegido
      (ver :mod:`control.anti_windup`).
    - derivada: diferencia hacia atrás de la MEDICIÓN, no del error:
      ``−(medida − medida_prev)/dt``. Con el setpoint fijo es lo mismo, pero
      evita el pico de la acción D ("derivative kick") cuando el error salta,
      como en el primer paso. Si no hay medida previa (``None``) vale 0.
    - salida ``u`` saturada por :func:`escalar_u` a [0, límite de potencia].
    - ``cortada``: el interruptor del horno está apagado y la salida no llega.
      Con anti-windup (recorte o condicional) la integral se congela; sin
      anti-windup sigue acumulando (windup, y sobrepaso al volver a encender).
    """
    DT = dt
    if DT == 0:
        DT = 1e-6   # protección mínima

    integral_nueva = integral + 0.5 * (error + error_prev) * DT   # regla del trapecio
    derivada = 0.0 if medida_prev is None else -(medida - medida_prev) / DT
    proporcional = pid.KP * error

    u_bruta = (proporcional + pid.KI * integral_nueva + pid.KD * derivada) / limites.U_MAX
    tope = pid.limite_potencia
    if cortada and pid.anti_windup != "ninguno":
        pass                                   # salida cortada: la integral se congela
    else:
        integral = windout.limitar(pid.anti_windup, integral, integral_nueva, error, u_bruta,
                                   pid.restringir_integral, tope)

    u = proporcional + pid.KI * integral + pid.KD * derivada
    if math.isnan(u) or math.isinf(u):
        u = 0.0

    return escalar_u(u, limites.U_MAX, tope), integral, error, pid.KD * derivada, proporcional


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

    def paso(self, error, medida, dt, cortada=False):
        """Ejecuta un paso y devuelve ``u`` en [0, 1].

        ``medida`` es la temperatura que "lee" el controlador (T_SET − error,
        es decir, incluye las perturbaciones activas).
        """
        u, self.integral, self.error_prev, self.derivada, self.proporcional = calcular_pid(
            error, self.error_prev, self.integral, medida, self.medida_prev, self.parametros, dt, cortada
        )
        self.medida_prev = medida
        return u

    def seguir(self, u, error, medida, dt):
        """Modo manual: el PID no manda, pero SIGUE a la u que fija el usuario.

        Se ajusta la integral para que P + I + D dé exactamente esa u; así,
        al volver a automático, la potencia continúa desde donde estaba
        (transferencia sin salto).
        """
        p = self.parametros
        DT = dt if dt != 0 else 1e-6
        self.derivada = 0.0 if self.medida_prev is None else -p.KD * (medida - self.medida_prev) / DT
        self.proporcional = p.KP * error
        if p.KI:
            self.integral = (u * limites.U_MAX - self.proporcional - self.derivada) / p.KI
        self.error_prev = error
        self.medida_prev = medida
