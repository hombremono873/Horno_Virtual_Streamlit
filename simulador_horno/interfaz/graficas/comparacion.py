"""Ventana de comparación de métodos numéricos (pyqtgraph + PySide6).

Presenta un ``numerico.comparacion.ResultadoComparacion`` en tres vistas:

    ┌───────────────────────────────┬───────────────────────────────┐
    │ Temperatura: exacta vs.       │ Convergencia (log-log):       │
    │ Euler / Heun / RK4 (Δt mayor) │ error máximo vs. Δt           │
    ├───────────────────────────────┤ pendiente = orden del método  │
    │ |Error| en el tiempo (log)    │                               │
    └───────────────────────────────┴───────────────────────────────┘

A diferencia del monitor de simulación, esta ventana es estática: se
dibuja una vez y :meth:`mostrar_y_esperar` bloquea hasta que el usuario
la cierra.
"""
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from simulador_horno.estilos import tema
from simulador_horno.numerico.comparacion import solucion_exacta
from simulador_horno.numerico.integradores import NOMBRES, ORDEN

_DASH = QtCore.Qt.PenStyle.DashLine
_SIMBOLOS = {"euler": "o", "heun": "s", "rk4": "t"}


class VentanaComparacion:
    def __init__(self, resultado):
        self.app = pg.mkQApp(tema.VENTANA_TITULO)
        pg.setConfigOptions(antialias=True, background=tema.G_FONDO, foreground=tema.G_TEXTO)

        self.win = pg.GraphicsLayoutWidget(show=True, title="Comparación de métodos numéricos")
        self.win.resize(tema.VENTANA_ANCHO, tema.VENTANA_ALTO)

        dt_grande = max(resultado.dts)
        self._curvas(resultado, dt_grande)
        self._errores(resultado, dt_grande)
        self._convergencia(resultado)

        rejilla = self.win.ci.layout
        rejilla.setColumnStretchFactor(0, 3)
        rejilla.setColumnStretchFactor(1, 2)
        self.app.processEvents()

    # ------------------------------------------------------------------
    @staticmethod
    def _preparar(grafica, titulo):
        grafica.setTitle(titulo, size="11pt")
        grafica.showGrid(x=True, y=True, alpha=tema.G_CUADRICULA)
        grafica.setMenuEnabled(False)
        grafica.addLegend(offset=(-10, -10))
        grafica.getAxis("left").enableAutoSIPrefix(False)

    def _curvas(self, resultado, dt):
        g = self.win.addPlot(row=0, col=0)
        self._preparar(g, f"Temperatura: solución exacta vs. métodos  (Δt = {dt:g} s)")
        g.setLabel("left", "Temperatura (°C)")
        tray = resultado.trayectorias[("euler", dt)]
        # la exacta se dibuja densa para verse continua; los métodos, solo en sus pasos
        t_fino = np.linspace(0.0, tray.tiempos[-1], 2000)
        exacta = [solucion_exacta(t, tray.temperaturas[0]) for t in t_fino]
        g.plot(t_fino / 60.0, exacta, pen=pg.mkPen(tema.G_EXACTA, width=2, style=_DASH), name="Exacta")
        for metodo in NOMBRES:
            t = resultado.trayectorias[(metodo, dt)]
            g.plot(np.asarray(t.tiempos) / 60.0, t.temperaturas,
                   pen=pg.mkPen(tema.G_METODOS[metodo], width=1.5),
                   symbol=_SIMBOLOS[metodo], symbolSize=6,
                   symbolBrush=tema.G_METODOS[metodo], symbolPen=None, name=NOMBRES[metodo])

        self.p_curvas = g

    def _errores(self, resultado, dt):
        g = self.win.addPlot(row=1, col=0)
        self._preparar(g, f"|Error| = |T numérica − T exacta| en el tiempo  (Δt = {dt:g} s)")
        g.setLabel("left", "|Error| (°C, escala log)")
        g.setLabel("bottom", "Tiempo simulado (min)")
        g.setLogMode(x=False, y=True)
        g.setXLink(self.p_curvas)
        for metodo in NOMBRES:
            t = resultado.trayectorias[(metodo, dt)]
            # se omite t = 0, donde el error es exactamente cero (log indefinido)
            g.plot(np.asarray(t.tiempos[1:]) / 60.0, np.abs(t.errores[1:]),
                   pen=pg.mkPen(tema.G_METODOS[metodo], width=2), name=NOMBRES[metodo])

    def _convergencia(self, resultado):
        g = self.win.addPlot(row=0, col=1, rowspan=2)
        self._preparar(g, "Convergencia: error máximo vs. Δt  (log-log)")
        g.setLabel("left", "Error máximo (°C)")
        g.setLabel("bottom", "Δt (s)")
        g.setLogMode(x=True, y=True)
        dts = np.asarray(resultado.dts)
        # marcas justo en los Δt probados (en modo log, pyqtgraph ubica en log10)
        g.getAxis("bottom").setTicks([[(float(np.log10(dt)), f"{dt:g}") for dt in dts]])
        for metodo in NOMBRES:
            errores = [resultado.error(metodo, dt) for dt in resultado.dts]
            orden = float(np.mean(resultado.ordenes[metodo]))
            g.plot(dts, errores, pen=pg.mkPen(tema.G_METODOS[metodo], width=2),
                   symbol=_SIMBOLOS[metodo], symbolSize=9,
                   symbolBrush=tema.G_METODOS[metodo], symbolPen=None,
                   name=f"{NOMBRES[metodo]}: pendiente {orden:.2f} (teórica {ORDEN[metodo]})")

    # ------------------------------------------------------------------
    def mostrar_y_esperar(self):
        """Muestra la ventana y bloquea hasta que el usuario la cierra."""
        self.win.show()
        self.win.raise_()
        self.app.exec()
