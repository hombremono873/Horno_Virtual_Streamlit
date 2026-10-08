"""Acción derivativa sobre la medición: sin pico ("derivative kick") al arrancar."""
import pytest

from simulador_horno.configuracion.parametros import Configuracion, Perturbaciones
from simulador_horno.simulacion.simulador import Simulador


def test_sin_pico_en_el_primer_paso():
    sim = Simulador()
    sim.paso()
    assert sim.pid.derivada == 0.0     # antes: KD·970/DT = 19400


def test_equivale_a_derivar_el_error_con_setpoint_fijo():
    """Con T_SET constante, −Δmedida = Δerror: misma acción D salvo el primer paso."""
    config = Configuracion(perturbaciones=Perturbaciones(error_oscilante=True, flag_error=True))
    sim = Simulador(config, semilla=3)   # también con perturbaciones
    sim.paso()
    for _ in range(2000):
        error_prev = sim.pid.error_prev
        sim.paso()
        esperado = config.pid.KD * (sim.error - error_prev) / config.horno.DT
        assert sim.pid.derivada == pytest.approx(esperado, rel=1e-6, abs=1e-6)


def test_reiniciar_olvida_el_estado_del_pid():
    sim = Simulador()
    sim.avanzar(100)
    assert sim.pid.medida_prev is not None and sim.pid.proporcional != 0.0
    sim.reiniciar()
    assert sim.pid.medida_prev is None and sim.pid.proporcional == 0.0 and sim.pid.integral == 0.0
    assert sim.t == 0.0 and sim.historial.tiempos == []
