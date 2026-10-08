"""Perturbaciones sobre el horno (puerta, red, ambiente) y ruido del termopar."""
import random
import statistics

import pytest

from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.modelo import horno as modelo_horno
from simulador_horno.modelo.perturbaciones import (
    EventoAleatorio, factor_potencia_red, temperatura_ambiente,
)
from simulador_horno.simulacion.motor import Motor

HORAS = 4


def regimen(**perturbaciones):
    """Corre HORAS con las perturbaciones dadas; devuelve (motor, T reales y errores de 2 h a 4 h)."""
    random.seed(5)
    for atributo, valor in perturbaciones.items():
        setattr(vhorno, atributo, valor)
    motor = Motor()
    motor.avanzar(int(HORAS * 3600 / vhorno.DT))
    h = motor.historial
    return motor, h.temperaturas[2 * 3600:], h.errores[2 * 3600:]


def test_derivada_ideal_es_la_formula_original():
    vhorno.recalcular_B()
    for T, u in ((30.0, 1.0), (512.3, 0.37), (1000.0, 0.764)):
        original = (1 / vhorno.TAU) * (vhorno.T_AMB - T) + vhorno.B * u
        assert modelo_horno.derivada(T, u) == original      # bit a bit


def test_el_entorno_se_restaura_tras_cada_paso():
    regimen(puerta=True, red_variable=True, ambiente_variable=True)
    assert modelo_horno.entorno is modelo_horno.ENTORNO_IDEAL


def test_sin_perturbaciones_la_temperatura_queda_plana():
    _, T, _ = regimen()
    assert max(T) - min(T) < 0.05


def test_puerta_abierta_hace_caer_la_temperatura_y_el_pid_la_recupera():
    motor, T, _ = regimen(puerta=True)
    assert motor.aperturas >= 3
    assert min(T) < vhorno.T_SET - 20                       # caídas visibles
    assert abs(motor.T - vhorno.T_SET) < 10 or motor.puerta_abierta


def test_tasa_de_aperturas_independiente_de_dt():
    def contar(dt, horas=200):
        random.seed(9)
        evento, n = EventoAleatorio(), 0
        for k in range(int(horas * 3600 / dt)):
            _, nueva = evento.actualizar(k * dt, dt, limites.TASA_PUERTA_HORA, limites.DURACION_PUERTA)
            n += nueva
        return n
    gruesa, fina = contar(5.0), contar(1.0)
    esperado = 200 * limites.TASA_PUERTA_HORA / (1 + limites.TASA_PUERTA_HORA * limites.DURACION_PUERTA / 3600)
    assert gruesa == pytest.approx(esperado, rel=0.2)
    assert fina == pytest.approx(esperado, rel=0.2)


def test_red_variable_hace_oscilar_la_temperatura_alrededor_del_setpoint():
    _, T, _ = regimen(red_variable=True)
    assert statistics.pstdev(T) > 0.5
    assert abs(statistics.fmean(T) - vhorno.T_SET) < 1.0
    a = sum(limites.RED_AMPLITUDES)
    for t in range(0, 3600, 7):
        assert (1 - a) ** 2 <= factor_potencia_red(t, limites.RED_AMPLITUDES, limites.RED_PERIODOS) <= (1 + a) ** 2


def test_ambiente_variable_apenas_afecta_a_un_horno_controlado():
    assert temperatura_ambiente(900, 30.0, 10.0, 3600) == pytest.approx(40.0)   # cuarto de periodo
    _, T, _ = regimen(ambiente_variable=True)
    assert max(abs(x - vhorno.T_SET) for x in T) < 0.5


def test_ruido_del_termopar_afecta_la_lectura_no_al_horno():
    _, T, errores = regimen(ruido_termopar=True)
    assert statistics.pstdev(errores) == pytest.approx(limites.RUIDO_TERMOPAR_SIGMA, rel=0.15)
    assert statistics.pstdev(T) < 0.3


def test_apagar_las_perturbaciones_devuelve_el_horno_ideal():
    base = Motor()
    base.avanzar(20000)
    regimen(puerta=True, red_variable=True, ambiente_variable=True, ruido_termopar=True)
    for atributo, _, _ in limites.PERTURBACIONES:
        setattr(vhorno, atributo, False)
    otra = Motor()
    otra.avanzar(20000)
    assert otra.T == base.T
