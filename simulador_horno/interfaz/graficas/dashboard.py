"""Dashboard: curvas superpuestas de varias corridas guardadas (pyqtgraph).

Tres gráficas con el eje de tiempo enlazado: temperatura (con la línea del
setpoint), error visto por el controlador y potencia u. Cada corrida tiene
su color y su letra (A, B, C...), como en la tabla de la consola.

Ventana estática: :meth:`mostrar_y_esperar` bloquea hasta que se cierra.
"""
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore

from simulador_horno.estilos import tema
from simulador_horno.interfaz.consola.dashboard import LETRAS, etiqueta

_DASH = QtCore.Qt.PenStyle.DashLine
_DOT = QtCore.Qt.PenStyle.DotLine


class VentanaDashboard:
    def __init__(self, corridas):
        """``corridas``: lista de ``(parametros, series)`` de ``resultados.leer``."""
        self.app = pg.mkQApp(tema.VENTANA_TITULO)
        pg.setConfigOptions(antialias=True, background=tema.G_FONDO, foreground=tema.G_TEXTO)
        self.win = pg.GraphicsLayoutWidget(show=True, title="Comparación de corridas")
        self.win.resize(tema.VENTANA_ANCHO, tema.VENTANA_ALTO)

        self.p_temp = self._grafica(0, "Temperatura del horno", "Temperatura (°C)")
        self.p_err = self._grafica(1, "Error visto por el controlador", "Error (°C)")
        self.p_u = self._grafica(2, "Potencia del calentador u", "u")
        self.p_u.setLabel("bottom", "Tiempo simulado (min)")
        self.p_err.setXLink(self.p_temp)
        self.p_u.setXLink(self.p_temp)
        self.p_err.addLine(y=0, pen=pg.mkPen(tema.G_CERO, width=1, style=_DOT))
        self.p_u.setYRange(-0.05, 1.05, padding=0)

        setpoints = set()
        for i, (parametros, series) in enumerate(corridas):
            pen = pg.mkPen(tema.G_CORRIDAS[i], width=2)
            minutos = np.asarray(series["t_s"]) / 60.0
            nombre = f"{LETRAS[i]}: {etiqueta(parametros)}"
            self.p_temp.plot(minutos, series["T_C"], pen=pen, name=nombre)
            self.p_err.plot(minutos, series["error_C"], pen=pen)
            self.p_u.plot(minutos, series["u"], pen=pen)
            setpoints.update(series["T_set_C"][:1])
        for sp in setpoints:
            self.p_temp.addLine(y=sp, pen=pg.mkPen(tema.G_SETPOINT, width=1.5, style=_DASH))
        self.app.processEvents()

    def _grafica(self, fila, titulo, etiqueta_y):
        g = self.win.addPlot(row=fila, col=0)
        g.setTitle(titulo, size="11pt")
        g.showGrid(x=True, y=True, alpha=tema.G_CUADRICULA)
        g.getAxis("left").enableAutoSIPrefix(False)
        g.getAxis("left").setWidth(64)   # mismo ancho: el enlace del eje X queda alineado
        g.setLabel("left", etiqueta_y)
        g.setMenuEnabled(False)
        if fila == 0:
            g.addLegend(offset=(-10, -10))
        return g

    def mostrar_y_esperar(self):
        """Muestra la ventana y bloquea hasta que el usuario la cierra."""
        self.win.show()
        self.win.raise_()
        self.app.exec()
