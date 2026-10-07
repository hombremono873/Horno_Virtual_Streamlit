"""Ventana de monitorización en tiempo real (pyqtgraph + PySide6).

Un solo lienzo con cuatro vistas y una escala de color común:

    ┌───────────────────────────┬──────────────────┬──┐
    │ Temperatura vs. tiempo    │  PAREDES DEL     │°C│
    ├───────────────────────────┤  HORNO           │  │
    │ Error de control vs. t    │  (colorimetría)  │  │
    ├───────────────────────────┴──────────────────┴──┤
    │ Evolución del color térmico (histórico)          │
    └────────────────────────────────────────────────┘

- "Temperatura vs. tiempo" da la **tendencia** del control.
- "Paredes del horno" es la **colorimetría** de la planta: un corte del
  horno cuyas paredes se iluminan con el color de la temperatura actual
  (aspecto real del proceso), con la lectura numérica al centro.
- "Evolución del color térmico" es el histórico de esa colorimetría.
- La franja de la derecha es la escala de color en °C.

El bucle de simulación es síncrono: cada paso llama a :meth:`actualizar`,
que refresca los datos y procesa los eventos de Qt (equivale al antiguo
``fig.canvas.flush_events()`` de matplotlib).
"""
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

from simulador_horno.config import limites, tema
from simulador_horno.config import parametros_horno as vhorno

_DASH = QtCore.Qt.PenStyle.DashLine
_DOT = QtCore.Qt.PenStyle.DotLine


def _mascara_paredes(alto=24, ancho=32, grosor=5):
    """Máscara booleana con el marco (paredes) del horno en True."""
    m = np.zeros((alto, ancho), dtype=bool)
    m[:grosor, :] = m[-grosor:, :] = True
    m[:, :grosor] = m[:, -grosor:] = True
    return m


class PanelGraficas:
    def __init__(self):
        self.app = pg.mkQApp(tema.VENTANA_TITULO)
        pg.setConfigOptions(antialias=True, background=tema.G_FONDO, foreground=tema.G_TEXTO)

        self.win = pg.GraphicsLayoutWidget(show=True, title=tema.VENTANA_TITULO)
        self.win.resize(tema.VENTANA_ANCHO, tema.VENTANA_ALTO)

        self._lut = pg.colormap.get(tema.MAPA_TERMICO).getLookupTable(0.0, 1.0, 256)
        self._niveles = (limites.TEMP_MIN_COLOR, limites.TEMP_MAX_COLOR)

        # -- Tendencia: temperatura vs. tiempo -----------------------
        self.p_temp = self.win.addPlot(row=0, col=0)
        self.p_temp.setTitle("Temperatura del horno — tendencia", size="11pt")
        self.p_temp.showGrid(x=True, y=True, alpha=tema.G_CUADRICULA)
        self.p_temp.setLabel("left", "Temperatura", units="°C")
        self.p_temp.addLegend(offset=(-10, 10))
        self.c_temp = self.p_temp.plot(pen=pg.mkPen(tema.G_TEMP, width=2), name="Temperatura")
        self.l_sp = self.p_temp.addLine(
            y=0, pen=pg.mkPen(tema.G_SETPOINT, width=1.5, style=_DASH), label="Setpoint"
        )

        # -- Error de control vs. tiempo ----------------------------
        self.p_err = self.win.addPlot(row=1, col=0)
        self.p_err.setTitle("Error de control  (setpoint − temperatura)", size="11pt")
        self.p_err.showGrid(x=True, y=True, alpha=tema.G_CUADRICULA)
        self.p_err.setLabel("left", "Error", units="°C")
        self.p_err.setLabel("bottom", "Tiempo", units="s")
        self.p_err.setXLink(self.p_temp)
        self.p_err.addLine(y=0, pen=pg.mkPen(tema.G_CERO, width=1, style=_DOT))
        self.c_err = self.p_err.plot(pen=pg.mkPen(tema.G_ERROR, width=2))

        # -- Colorimetría de las paredes del horno ------------------
        self.p_horno = self.win.addPlot(row=0, col=1, rowspan=2)
        self.p_horno.setTitle("Paredes del horno — colorimetría", size="11pt")
        self.p_horno.hideAxis("left")
        self.p_horno.hideAxis("bottom")
        self.p_horno.setMouseEnabled(x=False, y=False)
        self.p_horno.setAspectLocked(True)
        self._mascara = _mascara_paredes()
        self.img_horno = pg.ImageItem(axisOrder="row-major")
        self.img_horno.setLookupTable(self._lut)
        self.p_horno.addItem(self.img_horno)
        self.txt_horno = pg.TextItem(anchor=(0.5, 0.5), color="#ffffff",
                                     fill=pg.mkBrush(0, 0, 0, 160))
        _fuente = QtGui.QFont()
        _fuente.setPointSize(20)
        _fuente.setBold(True)
        self.txt_horno.setFont(_fuente)
        alto, ancho = self._mascara.shape
        self.txt_horno.setPos(ancho / 2, alto / 2)
        self.p_horno.addItem(self.txt_horno)

        # -- Escala de color en °C ---------------------------------
        self.p_escala = self.win.addPlot(row=0, col=2, rowspan=2)
        self.p_escala.setTitle("°C", size="11pt")
        self.p_escala.hideAxis("bottom")
        self.p_escala.getAxis("left").setWidth(52)
        self.p_escala.setMouseEnabled(x=False, y=False)
        lo, hi = self._niveles
        img_escala = pg.ImageItem(np.linspace(lo, hi, 256).reshape(-1, 1), axisOrder="row-major")
        img_escala.setLookupTable(self._lut)
        img_escala.setLevels(self._niveles)
        img_escala.setRect(QtCore.QRectF(0.0, lo, 1.0, hi - lo))
        self.p_escala.addItem(img_escala)
        self.p_escala.setXRange(0, 1, padding=0)
        self.p_escala.setYRange(lo, hi, padding=0)
        self.p_escala.getAxis("bottom").setStyle(showValues=False)

        # -- Evolución del color térmico (histórico) ----------------
        self.p_img = self.win.addPlot(row=2, col=0, colspan=3)
        self.p_img.setTitle("Evolución del color térmico del horno", size="11pt")
        self.p_img.setLabel("bottom", "Tiempo", units="s")
        self.p_img.hideAxis("left")
        self.p_img.setMouseEnabled(x=False, y=False)
        self.p_img.setMaximumHeight(150)
        self.img_franja = pg.ImageItem(axisOrder="row-major")
        self.img_franja.setLookupTable(self._lut)
        self.p_img.addItem(self.img_franja)
        self._franja = []

        rejilla = self.win.ci.layout
        rejilla.setColumnStretchFactor(0, 6)
        rejilla.setColumnStretchFactor(1, 3)
        rejilla.setColumnStretchFactor(2, 0)
        rejilla.setColumnFixedWidth(2, 104)

        self.win.show()
        self.app.processEvents()

    # ------------------------------------------------------------------
    @property
    def abierta(self) -> bool:
        """False cuando el usuario ha cerrado la ventana."""
        return self.win.isVisible()

    def actualizar(self, tiempos, temperaturas, errores, T, T_set):
        # tendencia + error
        self.c_temp.setData(tiempos, temperaturas)
        self.c_err.setData(tiempos, errores)
        self.l_sp.setValue(T_set)

        # colorimetría de las paredes (paredes a T, cavidad algo más fría)
        t_cavidad = vhorno.T_AMB + 0.8 * (T - vhorno.T_AMB)
        marco = np.full(self._mascara.shape, t_cavidad, dtype=float)
        marco[self._mascara] = T
        self.img_horno.setImage(marco, autoLevels=False, levels=self._niveles)
        self.txt_horno.setText(f"{T:.0f} °C")

        # histórico de color
        self._franja.append(float(T))
        fila = np.asarray(self._franja, dtype=float).reshape(1, -1)
        if tiempos:
            self.img_franja.setRect(QtCore.QRectF(0.0, 0.0, float(tiempos[-1]) or 1.0, 1.0))
        self.img_franja.setImage(fila, autoLevels=False, levels=self._niveles)

        self.app.processEvents()

    def cerrar(self):
        self.win.close()
        self.app.processEvents()
