"""Arranque en frío o en caliente (ParametrosHorno.T_INICIAL)."""
import pytest

from simulador_horno.configuracion.parametros import Configuracion, ParametrosHorno
from simulador_horno.simulacion.simulador import Simulador


def corrida(T_inicial, horas=2):
    sim = Simulador(Configuracion(horno=ParametrosHorno(T_INICIAL=T_inicial)))
    sim.avanzar(int(horas * 3600 / sim.config.horno.DT))
    return sim, sim.metricas()


def test_por_defecto_es_arranque_en_frio():
    horno = ParametrosHorno()
    assert horno.T_INICIAL == horno.T_AMB
    assert Simulador().T == horno.T_AMB


@pytest.mark.parametrize("T_inicial", [30.0, 600.0, 900.0, 1200.0])
def test_la_corrida_empieza_en_t_inicial_y_llega_al_setpoint(T_inicial):
    sim, m = corrida(T_inicial)
    assert sim.historial.temperaturas[0] == T_inicial
    assert abs(m.error_final) < 0.5


def test_en_caliente_llega_antes():
    _, frio = corrida(30.0)
    _, caliente = corrida(600.0)
    assert caliente.t90 < frio.t90
    assert caliente.t_establecimiento < frio.t_establecimiento


def test_por_encima_del_setpoint_se_enfria_sin_calentar():
    sim, m = corrida(1200.0)
    assert sim.historial.potencias[0] == 0.0         # el PID apaga la potencia
    assert sim.historial.temperaturas[100] < 1200.0  # y el horno se enfría
    assert m.sobrepaso_c > 0                         # se pasa por debajo antes de asentarse


def test_en_el_setpoint_no_hay_salto():
    _, m = corrida(ParametrosHorno().T_SET)
    assert not m.hay_salto
