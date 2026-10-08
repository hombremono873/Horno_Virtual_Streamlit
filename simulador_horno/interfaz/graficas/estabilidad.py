"""Ventana del estudio de estabilidad numérica (pyqtgraph + PySide6).

Una gráfica por cada Δt del ``ResultadoEstabilidad``, en rejilla 2×2: la
solución exacta del enfriamiento y los tres métodos. El eje Y se acota a
una banda alrededor del rango físico, de modo que las trayectorias que
divergen se ven salir del cuadro en lugar de aplastar la escala.

Ventana estática: :meth:`mostrar_y_esperar` bloquea hasta que se cierra.
"""
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.estilos import tema
from simulador_horno.numerico.comparacion import solucion_exacta
from simulador_horno.numerico.integradores import NOMBRES

_DASH = QtCore.Qt.PenStyle.DashLine
_DOT = QtCore.Qt.PenStyle.DotLine
_SIMBOLOS = {"euler": "o", "heun": "s", "rk4": "t"}
_COLUMNAS = 2


class VentanaEstabilidad:
    def __init__(self, resultado):
        self.app = pg.mkQApp(tema.VENTANA_TITULO)
        pg.setConfigOptions(antialias=True, background=tema.G_FONDO, foreground=tema.G_TEXTO)

        self.win = pg.GraphicsLayoutWidget(show=True, title="Estabilidad de los métodos numéricos")
        self.win.resize(tema.VENTANA_ANCHO, tema.VENTANA_ALTO)

        tau = vhorno.TAU
        salto = resultado.T0 - vhorno.T_AMB
        self._banda = (vhorno.T_AMB - 0.8 * salto, resultado.T0 + 0.8 * salto)
        for i, dt in enumerate(resultado.dts):
            self._grafica(resultado, dt, tau, fila=i // _COLUMNAS, col=i % _COLUMNAS)
        self.app.processEvents()

    def _grafica(self, resultado, dt, tau, fila, col):
        g = self.win.addPlot(row=fila, col=col)
        veredictos = ", ".join(f"{NOMBRES[m]} {resultado.veredicto(m, dt)}" for m in NOMBRES)
        g.setTitle(f"Δt = {dt:g} s = {dt / tau:g}·τ<br><span style='font-size:9pt'>{veredictos}</span>",
                   size="11pt")
        g.showGrid(x=True, y=True, alpha=tema.G_CUADRICULA)
        g.setMenuEnabled(False)
        g.setMouseEnabled(x=False, y=False)
        g.hideButtons()
        g.getAxis("left").enableAutoSIPrefix(False)
        g.setLabel("left", "Temperatura (°C)")
        g.setLabel("bottom", "Tiempo (t/τ)")
        g.addLegend(offset=(-10, 10))

        horizonte = resultado.trayectorias[("euler", dt)].tiempos[-1]
        t_fino = np.linspace(0.0, horizonte, 400)
        exacta = [solucion_exacta(t, resultado.T0, u=0.0) for t in t_fino]
        g.plot(t_fino / tau, exacta, pen=pg.mkPen(tema.G_EXACTA, width=2, style=_DASH), name="Exacta")
        g.addLine(y=vhorno.T_AMB, pen=pg.mkPen(tema.G_CERO, width=1, style=_DOT))
        for metodo in NOMBRES:
            tray = resultado.trayectorias[(metodo, dt)]
            g.plot(np.asarray(tray.tiempos) / tau, tray.temperaturas,
                   pen=pg.mkPen(tema.G_METODOS[metodo], width=1.5),
                   symbol=_SIMBOLOS[metodo], symbolSize=7,
                   symbolBrush=tema.G_METODOS[metodo], symbolPen=None, name=NOMBRES[metodo])
        g.setYRange(*self._banda, padding=0)
        g.setXRange(0, horizonte / tau, padding=0.02)

    def mostrar_y_esperar(self):
        """Muestra la ventana y bloquea hasta que el usuario la cierra."""
        self.win.show()
        self.win.raise_()
        self.app.exec()
