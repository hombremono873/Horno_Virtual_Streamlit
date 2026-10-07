"""Series temporales de la corrida en curso.

Las listas viven en ``parametros_horno`` porque las gráficas y la tabla en
vivo leen de ahí; esta clase solo centraliza el registro y el recorte.
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno


class Historial:
    def __init__(self, max_muestras=limites.MAX_MUESTRAS):
        self.max_muestras = max_muestras
        self.tiempos = vhorno.tiempos
        self.temperaturas = vhorno.temperaturas
        self.errores = vhorno.errores

    def registrar(self, t, T, error):
        self.tiempos.append(t)
        self.temperaturas.append(T)
        self.errores.append(error)
        self._recortar()

    def _recortar(self):
        exceso = len(self.tiempos) - self.max_muestras
        if exceso > 0:
            del self.tiempos[:exceso]
            del self.temperaturas[:exceso]
            del self.errores[:exceso]

    def limpiar(self):
        self.tiempos.clear()
        self.temperaturas.clear()
        self.errores.clear()
