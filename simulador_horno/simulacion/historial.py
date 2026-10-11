"""Series temporales de la corrida en curso.

Cada ``Historial`` tiene sus propias listas (cada simulador, el suyo).

Se guarda una muestra cada ``intervalo`` segundos SIMULADOS (no una por
paso), así el historial abarca horas de simulación a cualquier velocidad.

Series por muestra (todas del mismo instante t):

- ``tiempos``, ``temperaturas`` (real), ``setpoints``;
- ``errores``: el error que vio el controlador (incluye las perturbaciones
  de la medición; la temperatura medida es ``setpoint − error``);
- ``potencias``: la señal de control u en [0, 1];
- ``proporcionales``, ``integrales``, ``derivativos``: aporte de cada
  término del PID a la salida normalizada (u_bruta = P + I + D, antes de
  saturar a [0, 1]).
- ``alfas``, ``fracciones``: ángulo de disparo del triac (NaN en modo
  ideal) y fracción de potencia que REALMENTE llegó al horno;
- ``potencias_w``, ``energias_kwh``: potencia eléctrica (W) y energía
  consumida desde el inicio de la corrida (kWh).
"""
import math

from simulador_horno.configuracion import limites


class Historial:
    def __init__(self, max_muestras=limites.MAX_MUESTRAS, intervalo=limites.INTERVALO_MUESTREO):
        self.max_muestras = max_muestras
        self.intervalo = intervalo
        self.tiempos = []
        self.temperaturas = []
        self.errores = []
        self.potencias = []      # señal de control u en [0, 1]
        self.setpoints = []
        self.proporcionales = []
        self.integrales = []
        self.derivativos = []
        self.alfas = []
        self.fracciones = []
        self.potencias_w = []
        self.energias_kwh = []
        self._proxima = 0.0

    def _series(self):
        return (self.tiempos, self.temperaturas, self.errores, self.potencias,
                self.setpoints, self.proporcionales, self.integrales, self.derivativos,
                self.alfas, self.fracciones, self.potencias_w, self.energias_kwh)

    def registrar(self, t, T, error, u=0.0, T_set=None, P=0.0, I=0.0, D=0.0,
                  alfa=math.nan, fraccion=None, potencia_w=0.0, energia_kwh=0.0):
        """Guarda la muestra solo si ya pasó ``intervalo`` desde la anterior.

        ``T_set`` None = el setpoint que hace cero el error sin perturbaciones (T + error).
        """
        if t + 1e-9 < self._proxima:
            return
        self.tiempos.append(t)
        self.temperaturas.append(T)
        self.errores.append(error)
        self.potencias.append(u)
        self.setpoints.append(T + error if T_set is None else T_set)
        self.proporcionales.append(P)
        self.integrales.append(I)
        self.derivativos.append(D)
        self.alfas.append(alfa)
        self.fracciones.append(u if fraccion is None else fraccion)
        self.potencias_w.append(potencia_w)
        self.energias_kwh.append(energia_kwh)
        self._proxima += self.intervalo
        self._recortar()

    def _recortar(self):
        exceso = len(self.tiempos) - self.max_muestras
        if exceso > 0:
            for serie in self._series():
                del serie[:exceso]

    def limpiar(self):
        for serie in self._series():
            serie.clear()
        self._proxima = 0.0

    def __len__(self):
        return len(self.tiempos)
