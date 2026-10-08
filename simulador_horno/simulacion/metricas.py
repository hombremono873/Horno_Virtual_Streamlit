"""Métricas de desempeño de una corrida (sin E/S).

Se calculan sobre la temperatura REAL del horno (no sobre el error, que con
perturbaciones activas incluye lecturas falsas del sensor), a partir de las
series del historial (una muestra por segundo simulado).

Definiciones, con salto = T_SET − T0 (T0 = temperatura inicial):

- sobrepaso         : cuánto se pasa del setpoint en el sentido del salto,
                      en °C y en % del salto. Si el horno arranca por debajo es
                      el exceso por encima; si arranca por encima, por debajo.
- tiempo al 10 / 90 : primer instante en que recorre el 10 % / 90 % del salto.
- tiempo de subida  : t90 − t10.
- establecimiento   : instante desde el cual T queda SIEMPRE dentro de
                      ±BANDA_ESTABLECIMIENTO del salto alrededor del setpoint.
- error final       : T_SET − T al terminar.
- IAE = ∫|e| dt,  ISE = ∫e² dt   (e = T_SET − T; regla del trapecio).

Los tiempos que no se alcanzan durante la corrida valen None.
"""
from dataclasses import dataclass

BANDA_ESTABLECIMIENTO = 0.01   # ±1 % del salto
SALTO_MINIMO = 1.0             # °C; por debajo no tiene sentido hablar de subida


@dataclass
class Metricas:
    T0: float
    T_set: float
    duracion: float                 # s simulados analizados
    sobrepaso_c: float
    sobrepaso_pct: float
    t10: float | None
    t90: float | None
    t_subida: float | None
    t_establecimiento: float | None
    error_final: float
    iae: float
    ise: float

    @property
    def hay_salto(self):
        return abs(self.T_set - self.T0) >= SALTO_MINIMO


def _primer_cruce(tiempos, avance, fraccion):
    """Primer t en que el avance normalizado (0 en T0, 1 en el setpoint) llega a ``fraccion``."""
    for t, a in zip(tiempos, avance):
        if a >= fraccion:
            return t
    return None


def calcular(tiempos, temperaturas, T_set):
    """Métricas de la corrida a partir de sus series. ``None`` si no hay datos."""
    if len(tiempos) < 2:
        return None
    T0 = temperaturas[0]
    salto = T_set - T0
    errores = [T_set - T for T in temperaturas]

    iae = ise = 0.0
    for i in range(1, len(tiempos)):
        dt = tiempos[i] - tiempos[i - 1]
        iae += 0.5 * (abs(errores[i]) + abs(errores[i - 1])) * dt
        ise += 0.5 * (errores[i] ** 2 + errores[i - 1] ** 2) * dt

    if abs(salto) < SALTO_MINIMO:
        sobrepaso_c = sobrepaso_pct = 0.0
        t10 = t90 = t_subida = t_est = None
    else:
        sentido = 1.0 if salto > 0 else -1.0
        # cuánto se pasa del setpoint en el sentido del salto
        sobrepaso_c = max(0.0, max(sentido * (T - T_set) for T in temperaturas))
        sobrepaso_pct = sobrepaso_c / abs(salto) * 100
        avance = [(T - T0) / salto for T in temperaturas]
        t10 = _primer_cruce(tiempos, avance, 0.10)
        t90 = _primer_cruce(tiempos, avance, 0.90)
        t_subida = t90 - t10 if (t10 is not None and t90 is not None) else None
        banda = BANDA_ESTABLECIMIENTO * abs(salto)
        t_est = None
        for t, e in zip(tiempos, errores):
            if abs(e) > banda:
                t_est = None
            elif t_est is None:
                t_est = t

    return Metricas(
        T0=T0, T_set=T_set, duracion=tiempos[-1] - tiempos[0],
        sobrepaso_c=sobrepaso_c, sobrepaso_pct=sobrepaso_pct,
        t10=t10, t90=t90, t_subida=t_subida, t_establecimiento=t_est,
        error_final=errores[-1], iae=iae, ise=ise,
    )
