"""El historial guarda una muestra por segundo simulado y abarca al menos 4 horas."""
import pytest

from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.simulacion.historial import Historial
from simulador_horno.simulacion.motor import Motor


def test_conserva_4_horas_simuladas():
    assert limites.MAX_MUESTRAS * limites.INTERVALO_MUESTREO >= 4 * 3600
    motor = Motor()
    motor.avanzar(int(4.5 * 3600 / vhorno.DT))
    h = motor.historial
    assert h.tiempos[0] == pytest.approx(0.0)          # el arranque sigue ahí
    assert h.tiempos[-1] - h.tiempos[0] >= 4 * 3600 - 1
    assert len(h.tiempos) == len(h.temperaturas) == len(h.errores)


@pytest.mark.parametrize("dt", [0.1, 0.05])
def test_una_muestra_por_segundo_simulado_independiente_de_dt(dt):
    vhorno.DT = dt
    motor = Motor()
    motor.avanzar(int(round(600 / dt)))   # 10 min simulados
    tiempos = motor.historial.tiempos
    assert len(tiempos) == pytest.approx(600, abs=1)
    separaciones = [b - a for a, b in zip(tiempos, tiempos[1:])]
    assert all(s == pytest.approx(1.0, abs=dt + 1e-9) for s in separaciones)


def test_recorta_lo_mas_antiguo():
    h = Historial(max_muestras=10, intervalo=1.0)
    h.limpiar()
    for k in range(25):
        h.registrar(float(k), 0.0, 0.0)
    assert len(h.tiempos) == 10 and h.tiempos[0] == 15.0
