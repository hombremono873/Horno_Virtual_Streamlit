"""Acción derivativa sobre la medición: sin pico ("derivative kick") al arrancar."""
import random

import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.simulacion.motor import Motor


def test_sin_pico_en_el_primer_paso():
    Motor().paso()
    assert vpid.derivada == 0.0     # antes: KD·970/DT = 19400


def test_equivale_a_derivar_el_error_con_setpoint_fijo(monkeypatch):
    """Con T_SET constante, −Δmedida = Δerror: misma acción D salvo el primer paso."""
    random.seed(3)
    vhorno.error_oscilante = vhorno.flag_error = True   # también con perturbaciones
    motor = Motor()
    motor.paso()
    for _ in range(2000):
        error_prev = vpid.error_prev
        motor.paso()
        esperado = vpid.KD * (motor.error - error_prev) / vhorno.DT
        assert vpid.derivada == pytest.approx(esperado, rel=1e-6, abs=1e-6)


def test_cada_corrida_reinicia_la_medida_previa():
    motor = Motor()
    motor.avanzar(100)
    assert vpid.medida_prev is not None
    Motor()
    assert vpid.medida_prev is None
