"""Señal de control acotada a [0, 1] y desempeño de la corrida por defecto."""
import random

import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.control.escalado import escalar_u
from simulador_horno.interfaz.alarmas import sonora
from simulador_horno.simulacion.motor import Motor

HORAS = 4


@pytest.mark.parametrize("u_bruto, esperado", [(-1e9, 0.0), (-5.0, 0.0), (0.0, 0.0), (10000.0, 0.5), (1e9, 1.0)])
def test_escalar_u_satura_en_0_1(u_bruto, esperado):
    assert escalar_u(u_bruto) == pytest.approx(esperado)


@pytest.mark.parametrize("perturbaciones", [False, True])
def test_u_nunca_sale_de_0_1(perturbaciones, monkeypatch):
    monkeypatch.setattr(sonora, "alarma_impulso", lambda _: None)   # sin pitidos en pruebas
    random.seed(1234)
    vhorno.error_oscilante = vhorno.flag_error = perturbaciones
    motor = Motor()
    u_min, u_max = 1.0, 0.0
    for _ in range(int(HORAS * 3600 / vhorno.DT)):
        u, _ = motor.paso()
        u_min, u_max = min(u_min, u), max(u_max, u)
    assert 0.0 <= u_min and u_max <= 1.0


def metricas_corrida_por_defecto():
    """Corre 4 h simuladas: (t al 90 %, sobrepaso %, error final °C, establecimiento ±1 %)."""
    motor = Motor()
    salto = vhorno.T_SET - vhorno.T_AMB
    umbral_90 = vhorno.T_AMB + 0.9 * salto
    banda = 0.01 * salto
    t90 = t_est = None
    T_max = motor.T
    for _ in range(int(HORAS * 3600 / vhorno.DT)):
        motor.paso()
        T_max = max(T_max, motor.T)
        if t90 is None and motor.T >= umbral_90:
            t90 = motor.t
        if abs(vhorno.T_SET - motor.T) > banda:
            t_est = None
        elif t_est is None:
            t_est = motor.t
    sobrepaso = max(0.0, (T_max - vhorno.T_SET) / salto * 100)
    return t90, sobrepaso, vhorno.T_SET - motor.T, t_est


def test_corrida_por_defecto_alcanza_setpoint():
    t90, sobrepaso, error_final, t_est = metricas_corrida_por_defecto()
    print(
        f"\n  Corrida por defecto ({HORAS} h simuladas):"
        f"\n    tiempo al 90 %      : {t90 / 60:.1f} min"
        f"\n    sobrepaso           : {sobrepaso:.2f} %"
        f"\n    establecimiento ±1 %: {t_est / 60:.1f} min"
        f"\n    error final         : {error_final:+.4f} °C"
    )
    assert t90 is not None
    assert sobrepaso < 5.0
    assert t_est is not None          # entra y se queda en la banda de ±1 %
    assert abs(error_final) < 0.5
