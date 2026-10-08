"""Series temporales de la corrida en curso.

Las listas viven en ``parametros_horno`` porque las gráficas y la tabla en
vivo leen de ahí; esta clase solo centraliza el registro y el recorte.

Se guarda una muestra cada ``intervalo`` segundos SIMULADOS (no una por
paso), así el historial abarca horas de simulación a cualquier velocidad.
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno


class Historial:
    def __init__(self, max_muestras=limites.MAX_MUESTRAS, intervalo=limites.INTERVALO_MUESTREO):
        self.max_muestras = max_muestras
        self.intervalo = intervalo
        self.tiempos = vhorno.tiempos
        self.temperaturas = vhorno.temperaturas
        self.errores = vhorno.errores
        self.potencias = vhorno.potencias
        self._proxima = 0.0

    def _series(self):
        return (self.tiempos, self.temperaturas, self.errores, self.potencias)

    def registrar(self, t, T, error, u=0.0):
        """Guarda la muestra solo si ya pasó ``intervalo`` desde la anterior."""
        if t + 1e-9 < self._proxima:
            return
        self.tiempos.append(t)
        self.temperaturas.append(T)
        self.errores.append(error)
        self.potencias.append(u)
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
