"""Monitor gráfico: alineación de la franja y eje de tiempo con duración.

Se fuerza Qt sin pantalla (offscreen) antes de crear la aplicación, para
que la prueba no abra ventanas y funcione en cualquier equipo.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from simulador_horno.configuracion import parametros_horno as vhorno  # noqa: E402
from simulador_horno.interfaz.graficas.panel import PanelGraficas  # noqa: E402
from simulador_horno.simulacion.motor import Motor  # noqa: E402


@pytest.fixture
def panel():
    p = PanelGraficas()
    yield p
    p.cerrar()


def _fin_franja(panel):
    return panel.img_franja.mapRectToParent(panel.img_franja.boundingRect()).right()


def test_franja_alineada_con_las_curvas_mientras_crece(panel):
    """La franja terminaba más a la derecha que las curvas (setRect antes de setImage)."""
    motor = Motor()
    for refresco in range(1, 15):
        motor.avanzar(1500 * refresco)
        h = motor.historial
        panel.actualizar(h.tiempos, h.temperaturas, h.errores, motor.T, vhorno.T_SET)
        assert _fin_franja(panel) == pytest.approx(h.tiempos[-1] / 60.0)


def test_con_duracion_el_eje_abarca_la_corrida_completa(panel):
    motor = Motor()
    motor.avanzar(3000)                                   # solo 5 min de 120
    h = motor.historial
    panel.actualizar(h.tiempos, h.temperaturas, h.errores, motor.T, vhorno.T_SET, duracion=7200.0)
    x_min, x_max = panel.p_temp.viewRange()[0]
    assert x_min <= 0.0 and x_max >= 120.0
    assert panel.p_err.viewRange()[0] == panel.p_temp.viewRange()[0]   # error enlazado
