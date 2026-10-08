"""Modo "en vivo": cuántos pasos dar en cada refresco de la página.

El navegador refresca el monitor unas ``REFRESCO_HZ`` veces por segundo,
pero cada refresco puede tardar más de lo previsto (red, dibujo). Para que
la relación tiempo simulado / tiempo real siga siendo el factor elegido se
usa el tiempo REAL transcurrido desde el refresco anterior:

    pasos = factor · Δt_real / DT     (con la fracción acumulada, ver reloj)

La física no cambia: ``DT`` queda fijo. En "máxima" se calculan pasos
durante una fracción del periodo de refresco.
"""
import time

from simulador_horno.configuracion import limites
from simulador_horno.simulacion.reloj import pasos_por_refresco

LOTE_MAXIMA = 2000       # pasos entre consultas al reloj en modo "máxima"
FRACCION_MAXIMA = 0.6    # parte del periodo de refresco que se dedica a calcular en "máxima"
SALTO_MAXIMO = 1.0       # s reales: tras una pausa o un refresco muy lento no se "recupera" más


class EjecucionEnVivo:
    """Avanza un ``Simulador`` al ritmo de la velocidad elegida."""

    def __init__(self, simulador, hz=limites.REFRESCO_HZ, reloj=time.monotonic):
        self.sim = simulador
        self.hz = hz
        self._reloj = reloj
        self.reiniciar()

    def reiniciar(self):
        self._acumulado = 0.0
        self._ultimo = None
        self.impulsos_avisados = 0

    def pausar(self):
        """Al reanudar se empieza a contar desde ese momento (no se recupera la pausa)."""
        self._ultimo = None

    def refresco(self):
        """Avanza lo que corresponde a este refresco; devuelve los pasos dados."""
        if self.sim.terminada:
            return 0
        ahora = self._reloj()
        transcurrido = 1.0 / self.hz if self._ultimo is None else min(ahora - self._ultimo, SALTO_MAXIMO)
        self._ultimo = ahora
        factor = limites.VELOCIDADES.get(self.sim.config.simulacion.velocidad, 60)
        if factor is None:
            return self._maxima(ahora)
        if transcurrido <= 0:
            return 0
        pasos, self._acumulado = pasos_por_refresco(
            factor, self.sim.config.horno.DT, 1.0 / transcurrido, self._acumulado
        )
        return self.sim.avanzar_sin_pasarse(pasos)

    def _maxima(self, inicio):
        limite = inicio + FRACCION_MAXIMA / self.hz
        total = 0
        while self._reloj() < limite:
            dados = self.sim.avanzar_sin_pasarse(LOTE_MAXIMA)
            total += dados
            if dados < LOTE_MAXIMA:   # terminó la corrida
                break
        return total

    def impulsos_nuevos(self):
        """Impulsos ocurridos desde el último aviso (la interfaz decide cómo mostrarlos)."""
        nuevos = self.sim.impulsos - self.impulsos_avisados
        self.impulsos_avisados = self.sim.impulsos
        return nuevos
