"""El historial guarda una muestra por segundo simulado y abarca al menos 4 horas."""
import pytest

from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import Configuracion, ParametrosHorno
from simulador_horno.simulacion.historial import Historial
from simulador_horno.simulacion.simulador import Simulador


def test_conserva_4_horas_simuladas():
    assert limites.MAX_MUESTRAS * limites.INTERVALO_MUESTREO >= 4 * 3600
    sim = Simulador()
    sim.avanzar(int(4.5 * 3600 / sim.config.horno.DT))
    h = sim.historial
    assert h.tiempos[0] == pytest.approx(0.0)          # el arranque sigue ahí
    assert h.tiempos[-1] - h.tiempos[0] >= 4 * 3600 - 1
    assert len(h.tiempos) == len(h.temperaturas) == len(h.errores)


@pytest.mark.parametrize("dt", [0.1, 0.05])
def test_una_muestra_por_segundo_simulado_independiente_de_dt(dt):
    sim = Simulador(Configuracion(horno=ParametrosHorno(DT=dt)))
    sim.avanzar(int(round(600 / dt)))   # 10 min simulados
    tiempos = sim.historial.tiempos
    assert len(tiempos) == pytest.approx(600, abs=1)
    separaciones = [b - a for a, b in zip(tiempos, tiempos[1:])]
    assert all(s == pytest.approx(1.0, abs=dt + 1e-9) for s in separaciones)


def test_recorta_lo_mas_antiguo():
    h = Historial(max_muestras=10, intervalo=1.0)
    for k in range(25):
        h.registrar(float(k), 0.0, 0.0)
    assert len(h.tiempos) == 10 and h.tiempos[0] == 15.0


def test_cada_historial_tiene_sus_propias_listas():
    a, b = Historial(), Historial()
    a.registrar(0.0, 30.0, 970.0, 1.0)
    assert b.tiempos == [] and a.tiempos is not b.tiempos


def test_series_del_pid_y_setpoint():
    """P + I + D es la salida antes de saturar: recortada a [0, 1] da u."""
    sim = Simulador()
    sim.avanzar(int(2 * 3600 / sim.config.horno.DT))
    h = sim.historial
    assert len(h.setpoints) == len(h.proporcionales) == len(h.integrales) == len(h.derivativos) == len(h)
    assert set(h.setpoints) == {sim.config.horno.T_SET}
    for P, I, D, u in zip(h.proporcionales, h.integrales, h.derivativos, h.potencias):
        assert min(1.0, max(0.0, P + I + D)) == pytest.approx(u, abs=1e-12)
    assert h.proporcionales[0] > 1.0       # al arrancar, P solo ya satura
    assert h.integrales[-1] > 0.5          # en régimen, la integral sostiene la potencia


def test_el_setpoint_registrado_sigue_los_cambios():
    sim = Simulador()
    sim.avanzar(6000)
    sim.config.horno.T_SET = 800.0
    sim.avanzar(6000)
    assert sim.historial.setpoints[0] == 1000.0 and sim.historial.setpoints[-1] == 800.0
