"""Acción derivativa sobre la medición: sin pico ("derivative kick") al arrancar."""
import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.simulacion.motor import Motor


def test_sin_pico_en_el_primer_paso():
    motor = Motor()
    motor.paso()
    assert motor.pid.derivada == 0.0     # antes: KD·970/DT = 19400


def test_equivale_a_derivar_el_error_con_setpoint_fijo(monkeypatch):
    """Con T_SET constante, −Δmedida = Δerror: misma acción D salvo el primer paso."""
    vhorno.error_oscilante = vhorno.flag_error = True   # también con perturbaciones
    motor = Motor(semilla=3)
    motor.paso()
    for _ in range(2000):
        error_prev = motor.pid.error_prev
        motor.paso()
        esperado = vpid.KD * (motor.error - error_prev) / vhorno.DT
        assert motor.pid.derivada == pytest.approx(esperado, rel=1e-6, abs=1e-6)


def test_cada_corrida_tiene_su_propio_pid():
    motor = Motor()
    motor.avanzar(100)
    assert motor.pid.medida_prev is not None
    nueva = Motor()
    assert nueva.pid.medida_prev is None and nueva.pid.integral == 0.0
    assert nueva.pid is not motor.pid
