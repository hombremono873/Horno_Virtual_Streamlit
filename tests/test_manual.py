"""Modo manual (lazo abierto), límite de potencia y transferencia sin salto."""
import pytest

from simulador_horno.configuracion.parametros import Configuracion, Perturbaciones, ParametrosPID
from simulador_horno.simulacion.simulador import Simulador

HORA = 36_000   # pasos de 0,1 s


def simulador(**pid):
    return Simulador(Configuracion(pid=ParametrosPID(**pid)))


def test_manual_aplica_la_potencia_elegida():
    sim = simulador(modo_control="manual", potencia_manual=0.764)
    sim.avanzar(5 * HORA)                    # 6 constantes de tiempo
    assert set(sim.historial.potencias) == {0.764}
    # sin control, el horno va al equilibrio de esa potencia: 30 + 0,764 × 1270 ≈ 1000 °C
    assert sim.T == pytest.approx(30 + 0.764 * 1270, abs=3)


def test_manual_sube_mas_lento_que_el_pid():
    manual, auto = simulador(modo_control="manual", potencia_manual=0.764), simulador()
    manual.avanzar(2 * HORA)
    auto.avanzar(2 * HORA)
    assert manual.metricas().t90 > 1.5 * auto.metricas().t90


def test_en_manual_nadie_corrige_una_perturbacion():
    def con_puerta(modo):
        cfg = Configuracion(pid=ParametrosPID(modo_control=modo, potencia_manual=0.764),
                            perturbaciones=Perturbaciones(puerta=True))
        sim = Simulador(cfg, semilla=4)
        sim.avanzar(5 * HORA)
        return sim
    manual, auto = con_puerta("manual"), con_puerta("automatico")
    assert manual.aperturas == auto.aperturas > 0           # mismas aperturas (misma semilla)
    error_manual = abs(1000 - sum(manual.historial.temperaturas[-3600:]) / 3600)
    error_auto = abs(1000 - sum(auto.historial.temperaturas[-3600:]) / 3600)
    assert error_manual > 3 * error_auto


def test_transferencia_sin_salto():
    sim = simulador(modo_control="manual", potencia_manual=0.6)
    sim.avanzar(HORA)
    sim.config.pid.modo_control = "automatico"
    u_auto, error = sim.paso()
    # continúa donde estaba: solo cambia lo que la integral acumula en UN paso
    paso_integral = 10 * error * 0.1 / 20000
    assert u_auto == pytest.approx(0.6 + paso_integral, abs=1e-3)
    # sin el seguimiento la integral valdría 0 y solo P (200 × error) saturaría u en 1
    assert 200 * error / 20000 > 1
    sim.avanzar(4 * HORA)
    assert sim.T == pytest.approx(1000.0, abs=0.5)          # y después el PID lleva al setpoint


def test_limite_de_potencia():
    sim = simulador(limite_potencia=0.6)
    sim.avanzar(5 * HORA)
    assert max(sim.historial.potencias) == pytest.approx(0.6)
    # no alcanza el setpoint: el máximo posible es 30 + 0,6 × 1270 = 792 °C
    assert sim.T == pytest.approx(30 + 0.6 * 1270, abs=5) and sim.T < 1000


def test_con_limite_el_anti_windup_condicional_no_infla_la_integral():
    def integral_maxima(anti_windup):
        sim = simulador(limite_potencia=0.6, anti_windup=anti_windup)
        maximo = 0.0
        for _ in range(2 * HORA):
            sim.paso()
            maximo = max(maximo, abs(sim.pid.integral))
        return maximo
    assert integral_maxima("condicional") < integral_maxima("ninguno") / 10
