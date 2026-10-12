"""Acción derivativa sobre la medición: sin pico ("derivative kick") al arrancar."""
import pytest

from simulador_horno.configuracion.parametros import Configuracion, ParametrosPID, Perturbaciones
from simulador_horno.simulacion.simulador import Simulador


def test_sin_pico_en_el_primer_paso():
    sim = Simulador()
    sim.paso()
    assert sim.pid.derivada == 0.0     # antes: KD·970/DT = 19400


def test_equivale_a_derivar_el_error_con_setpoint_fijo():
    """Con T_SET constante, −Δmedida = Δerror: misma acción D salvo el primer paso."""
    config = Configuracion(pid=ParametrosPID(filtro_derivada=0.0),     # derivada cruda
                           perturbaciones=Perturbaciones(error_oscilante=True, flag_error=True))
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


def test_el_filtro_suaviza_el_ruido_del_termopar():
    """Sin filtro, ±1 °C de ruido cada 0,1 s parece ±10 °C/s y la potencia salta."""
    import statistics

    def oscilacion(filtro):
        cfg = Configuracion(pid=ParametrosPID(KD=2000, filtro_derivada=filtro),
                            perturbaciones=Perturbaciones(ruido_termopar=True))
        sim = Simulador(cfg, semilla=1)
        sim.avanzar(2 * 36000)                       # régimen
        us = []
        for _ in range(36000):
            us.append(sim.paso()[0])
        return statistics.pstdev(us)
    sin_filtro, con_filtro = oscilacion(0.0), oscilacion(10.0)
    assert sin_filtro > 0.25 and con_filtro < 0.03          # medido: 38 % contra 2 %


def test_filtro_de_primer_orden():
    from simulador_horno.control.pid import derivada_de_la_medicion
    assert derivada_de_la_medicion(10.0, None, 5.0, 10.0, 0.1) == 0.0          # sin medida previa
    assert derivada_de_la_medicion(10.0, 9.0, 0.0, 0.0, 0.1) == pytest.approx(-10.0)   # sin filtro: cruda
    # con filtro de 10 s, en un paso de 0,1 s se avanza 0,1/10,1 del camino hacia la cruda
    assert derivada_de_la_medicion(10.0, 9.0, 0.0, 10.0, 0.1) == pytest.approx(-10.0 * 0.1 / 10.1)


def test_valores_por_defecto_de_la_derivada():
    p = ParametrosPID()
    assert p.KD == 2000 and p.filtro_derivada == 10.0
