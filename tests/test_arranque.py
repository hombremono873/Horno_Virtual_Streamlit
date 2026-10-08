"""Arranque en frío o en caliente (parametros_horno.T_INICIAL)."""
import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.simulacion.metricas import calcular
from simulador_horno.simulacion.motor import Motor


def corrida(T_inicial, horas=2):
    vhorno.T_INICIAL = T_inicial
    motor = Motor()
    motor.avanzar(int(horas * 3600 / vhorno.DT))
    h = motor.historial
    return motor, calcular(h.tiempos, h.temperaturas, vhorno.T_SET)


def test_por_defecto_es_arranque_en_frio():
    assert vhorno.T_INICIAL == vhorno.T_AMB
    assert Motor().T == vhorno.T_AMB


@pytest.mark.parametrize("T_inicial", [30.0, 600.0, 900.0, 1200.0])
def test_la_corrida_empieza_en_t_inicial_y_llega_al_setpoint(T_inicial):
    motor, m = corrida(T_inicial)
    assert motor.historial.temperaturas[0] == T_inicial
    assert abs(m.error_final) < 0.5


def test_en_caliente_llega_antes():
    _, frio = corrida(30.0)
    _, caliente = corrida(600.0)
    assert caliente.t90 < frio.t90
    assert caliente.t_establecimiento < frio.t_establecimiento


def test_por_encima_del_setpoint_se_enfria_sin_calentar():
    motor, m = corrida(1200.0)
    assert motor.historial.potencias[0] == 0.0         # el PID apaga la potencia
    assert motor.historial.temperaturas[100] < 1200.0  # y el horno se enfría
    assert m.sobrepaso_c > 0                           # se pasa por debajo antes de asentarse


def test_en_el_setpoint_no_hay_salto():
    _, m = corrida(vhorno.T_SET)
    assert not m.hay_salto
