"""Métricas de desempeño (simulacion.metricas) contra resultados conocidos."""
import math

import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.simulacion.metricas import calcular
from simulador_horno.simulacion.motor import Motor

TAU = 600.0


def primer_orden(T0, T_set, horas=3.0):
    """T(t) = T_set + (T0 − T_set)·e^(−t/τ), una muestra por segundo."""
    tiempos = [float(t) for t in range(int(horas * 3600) + 1)]
    return tiempos, [T_set + (T0 - T_set) * math.exp(-t / TAU) for t in tiempos]


def test_respuesta_de_primer_orden_coincide_con_la_teoria():
    tiempos, temps = primer_orden(30.0, 1000.0)
    m = calcular(tiempos, temps, 1000.0)
    assert m.sobrepaso_c == pytest.approx(0.0, abs=1e-9)
    assert m.t10 == pytest.approx(TAU * math.log(1 / 0.9), abs=1.0)    # 63 s
    assert m.t90 == pytest.approx(TAU * math.log(10), abs=1.0)         # 1382 s
    assert m.t_establecimiento == pytest.approx(TAU * math.log(100), abs=1.0)
    assert m.iae == pytest.approx(970.0 * TAU, rel=1e-3)               # ∫ 970·e^(−t/τ) dt
    assert m.ise == pytest.approx(970.0 ** 2 * TAU / 2, rel=1e-3)
    assert m.error_final == pytest.approx(0.0, abs=1e-3)


def test_sobrepaso():
    tiempos = [0.0, 1.0, 2.0, 3.0, 4.0]
    temps = [30.0, 600.0, 1048.5, 990.0, 1000.0]
    m = calcular(tiempos, temps, 1000.0)
    assert m.sobrepaso_c == pytest.approx(48.5)
    assert m.sobrepaso_pct == pytest.approx(5.0)


def test_arranque_por_encima_del_setpoint():
    """Horno caliente que se enfría hasta el setpoint: el 'sobrepaso' es por debajo."""
    tiempos, temps = primer_orden(1200.0, 1000.0)
    temps[3000] = 990.0                         # se pasa 10 °C por debajo
    m = calcular(tiempos, temps, 1000.0)
    assert m.sobrepaso_c == pytest.approx(10.0)
    assert m.sobrepaso_pct == pytest.approx(5.0)
    assert m.t90 == pytest.approx(TAU * math.log(10), abs=1.0)


def test_arranque_en_el_setpoint_no_tiene_subida():
    m = calcular([0.0, 1.0, 2.0], [1000.0, 1000.2, 999.9], 1000.0)
    assert not m.hay_salto
    assert m.t90 is None and m.sobrepaso_c == 0.0


def test_no_se_estabiliza():
    tiempos, temps = primer_orden(30.0, 1000.0, horas=0.2)   # se corta a mitad de la subida
    m = calcular(tiempos, temps, 1000.0)
    assert m.t_establecimiento is None and m.t90 is None


def test_sin_datos():
    assert calcular([], [], 1000.0) is None
    assert calcular([0.0], [30.0], 1000.0) is None


def test_corrida_real_por_defecto():
    motor = Motor()
    motor.avanzar(int(2 * 3600 / vhorno.DT))
    h = motor.historial
    m = calcular(h.tiempos, h.temperaturas, vhorno.T_SET)
    assert m.sobrepaso_pct == pytest.approx(0.54, abs=0.05)
    assert m.t90 / 60 == pytest.approx(58.2, abs=0.5)
    assert m.t_establecimiento / 60 == pytest.approx(70.6, abs=0.5)


def test_las_metricas_distinguen_los_anti_windup():
    resultados = {}
    for modo in ("ninguno", "condicional"):
        vpid.anti_windup = modo
        motor = Motor()
        motor.avanzar(int(2 * 3600 / vhorno.DT))
        h = motor.historial
        resultados[modo] = calcular(h.tiempos, h.temperaturas, vhorno.T_SET)
    assert resultados["ninguno"].sobrepaso_pct > 10 > resultados["condicional"].sobrepaso_pct
    assert resultados["ninguno"].iae > resultados["condicional"].iae
