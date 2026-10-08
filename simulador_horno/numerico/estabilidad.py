"""Estabilidad numérica de Euler, Heun y RK4 con pasos Δt grandes.

Escenario: el horno a T0 = T_SET se enfría con la potencia apagada (u = 0).

    dT/dt = −(T − T_AMB)/TAU        →   T(t) = T_AMB + (T0 − T_AMB)·e^(−t/TAU)

Es la ecuación de prueba y' = λ·y con λ = −1/TAU sobre la desviación
y = T − T_AMB. Cada método multiplica la desviación por un factor fijo en
cada paso, el factor de amplificación R(z) con z = λ·Δt = −Δt/TAU:

    Euler   R = 1 + z
    Heun    R = 1 + z + z²/2
    RK4     R = 1 + z + z²/2 + z³/6 + z⁴/24

    |R| < 1  estable    (R < 0: oscila alrededor de T_AMB pero converge)
    |R| > 1  inestable  (la desviación crece en cada paso: diverge)

La física es estable para cualquier Δt; la inestabilidad es del método.
Límites sobre el eje real: Euler y Heun Δt < 2·TAU; RK4 Δt < ~2,785·TAU.

Sin E/S: devuelve datos que la interfaz presenta (tabla y gráficas).
"""
from dataclasses import dataclass

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.numerico.comparacion import integrar
from simulador_horno.numerico.integradores import METODOS

# Δt de prueba como múltiplos de TAU: estable, oscilante, diverge Euler/Heun, diverge RK4.
FRACCIONES_TAU = (0.5, 1.5, 2.5, 3.0)
HORIZONTE_TAU = 12   # duración de cada integración, en constantes de tiempo

_COEFICIENTES = {    # R(z) = Σ c_k·z^k  (desarrollo de Taylor de e^z truncado)
    "euler": (1, 1),
    "heun": (1, 1, 1 / 2),
    "rk4": (1, 1, 1 / 2, 1 / 6, 1 / 24),
}


def factor_amplificacion(metodo, dt, tau=None):
    """R(z) con z = −dt/tau: factor por el que el método multiplica la desviación."""
    z = -dt / (tau or vhorno.TAU)
    return sum(c * z ** k for k, c in enumerate(_COEFICIENTES[metodo]))


def clasificar(R):
    if abs(R) > 1:
        return "diverge"
    return "oscila" if R < 0 else "estable"


def limite_estabilidad(metodo, tau=None):
    """Mayor Δt estable (s): raíz de |R(−Δt/τ)| = 1 en (0, 4τ], por bisección."""
    tau = tau or vhorno.TAU
    bajo, alto = 0.1 * tau, 4.0 * tau    # en 0,1τ es estable; en 4τ ninguno lo es
    for _ in range(60):
        medio = (bajo + alto) / 2
        if abs(factor_amplificacion(metodo, medio, tau)) <= 1:
            bajo = medio
        else:
            alto = medio
    return bajo


@dataclass
class ResultadoEstabilidad:
    T0: float
    dts: tuple
    trayectorias: dict      # (metodo, dt) -> comparacion.Trayectoria
    factores: dict          # (metodo, dt) -> R
    limites: dict           # metodo -> Δt máximo estable (s)

    def veredicto(self, metodo, dt):
        return clasificar(self.factores[(metodo, dt)])


def estudiar(fracciones=FRACCIONES_TAU, horizonte_tau=HORIZONTE_TAU):
    """Integra el enfriamiento libre con cada método y cada Δt = fracción·TAU."""
    tau = vhorno.TAU
    T0 = vhorno.T_SET
    dts = tuple(f * tau for f in fracciones)
    trayectorias, factores = {}, {}
    for metodo in METODOS:
        for dt in dts:
            trayectorias[(metodo, dt)] = integrar(metodo, dt, horizonte_tau * tau, u=0.0, T0=T0)
            factores[(metodo, dt)] = factor_amplificacion(metodo, dt, tau)
    limites = {m: limite_estabilidad(m, tau) for m in METODOS}
    return ResultadoEstabilidad(T0, dts, trayectorias, factores, limites)
