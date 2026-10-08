"""Comparación de los métodos numéricos con la solución exacta.

Con potencia constante ``u`` la ecuación del horno

    dT/dt = (1/TAU)·(T_AMB − T) + B·u

tiene solución analítica:

    T(t) = T_eq + (T0 − T_eq)·e^(−t/TAU),     T_eq = T_AMB + B·u·TAU

Integrando la misma ecuación con Euler, Heun y RK4 para varios ``Δt`` se
mide el error de cada método frente a la exacta y su orden de convergencia
observado: si el error de un método de orden p es ~C·Δt^p, entonces

    p ≈ log2( e(Δt) / e(Δt/2) )

Sin E/S: devuelve datos que la interfaz presenta (tabla y gráficas).
"""
import math
from dataclasses import dataclass, field

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.numerico.integradores import EVALUACIONES, METODOS

# Δt de prueba (s): cada uno es la mitad del anterior, para estimar el orden.
DTS_COMPARACION = (240.0, 120.0, 60.0, 30.0, 15.0)
HORIZONTE = 3600.0   # s simulados: la primera hora de calentamiento
U_CONSTANTE = 1.0    # potencia plena, como en la subida real


def solucion_exacta(t, T0, u=U_CONSTANTE):
    T_eq = vhorno.T_AMB + vhorno.B * u * vhorno.TAU
    return T_eq + (T0 - T_eq) * math.exp(-t / vhorno.TAU)


@dataclass
class Trayectoria:
    """Una integración completa con un método y un Δt."""
    metodo: str
    dt: float
    tiempos: list = field(default_factory=list)
    temperaturas: list = field(default_factory=list)
    errores: list = field(default_factory=list)   # T_numérica − T_exacta en cada paso

    @property
    def error_maximo(self):
        return max(abs(e) for e in self.errores)

    @property
    def evaluaciones(self):
        """Costo: veces que se evaluó dT/dt (pasos × evaluaciones por paso)."""
        return (len(self.tiempos) - 1) * EVALUACIONES[self.metodo]


@dataclass
class ResultadoComparacion:
    dts: tuple
    trayectorias: dict          # (metodo, dt) -> Trayectoria
    ordenes: dict               # metodo -> [orden observado entre dts[i] y dts[i+1]]

    def error(self, metodo, dt):
        return self.trayectorias[(metodo, dt)].error_maximo


def integrar(metodo, dt, horizonte=HORIZONTE, u=U_CONSTANTE):
    """Integra con ``metodo`` y paso ``dt`` desde T_AMB hasta ``horizonte``.

    Los métodos leen ``parametros_horno.DT``: se cambia solo durante la
    integración y se restaura siempre al terminar.
    """
    paso = METODOS[metodo]
    dt_usuario = vhorno.DT
    T0 = vhorno.T_AMB
    tray = Trayectoria(metodo, dt, [0.0], [T0], [0.0])
    try:
        vhorno.DT = dt
        T = T0
        for k in range(1, int(round(horizonte / dt)) + 1):
            T = paso(T, u)
            t = k * dt
            tray.tiempos.append(t)
            tray.temperaturas.append(T)
            tray.errores.append(T - solucion_exacta(t, T0, u))
    finally:
        vhorno.DT = dt_usuario
    return tray


def comparar(dts=DTS_COMPARACION, horizonte=HORIZONTE, u=U_CONSTANTE):
    """Integra con todos los métodos y todos los ``dts``; calcula los órdenes."""
    vhorno.recalcular_B()
    trayectorias = {(m, dt): integrar(m, dt, horizonte, u) for m in METODOS for dt in dts}
    ordenes = {}
    for m in METODOS:
        errores = [trayectorias[(m, dt)].error_maximo for dt in dts]
        ordenes[m] = [
            math.log(e1 / e2) / math.log(dt1 / dt2) if e2 > 0 else float("nan")
            for (dt1, e1), (dt2, e2) in zip(zip(dts, errores), zip(dts[1:], errores[1:]))
        ]
    return ResultadoComparacion(tuple(dts), trayectorias, ordenes)
