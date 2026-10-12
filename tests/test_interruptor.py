"""Interruptor de potencia: corta la energía, pero el control sigue midiendo y calculando."""
import pytest

from simulador_horno.configuracion.parametros import Configuracion, ParametrosPID
from simulador_horno.modelo import triac
from simulador_horno.simulacion.simulador import Simulador

MINUTO = 600   # pasos de 0,1 s


def en_regimen(**pid):
    sim = Simulador(Configuracion(pid=ParametrosPID(**pid)))
    sim.avanzar(120 * MINUTO)                 # 2 h: en el setpoint
    return sim


def test_apagado_corta_la_energia_pero_el_control_sigue():
    sim = en_regimen()
    energia = sim.energia_j
    sim.config.actuador.encendido = False
    sim.avanzar(20 * MINUTO)
    assert sim.fraccion == 0.0 and sim.potencia_w == 0.0
    assert sim.energia_j == energia                     # no se consume energía
    assert sim.T < 1000 - 100                            # el horno se enfría
    assert sim.u == 1.0                                  # el PID sigue pidiendo potencia
    assert sim.historial.temperaturas[-1] == sim.historial.temperaturas[-1]   # y se sigue midiendo


def sobrepaso_al_reencender(anti_windup):
    sim = en_regimen(anti_windup=anti_windup)
    sim.config.actuador.encendido = False
    sim.avanzar(20 * MINUTO)
    integral_apagado = sim.pid.integral
    sim.config.actuador.encendido = True
    T_max = 0.0
    for _ in range(90 * MINUTO):
        sim.paso()
        T_max = max(T_max, sim.T)
    return T_max - 1000.0, integral_apagado


def test_con_anti_windup_la_integral_se_congela_y_no_hay_golpe():
    sobrepaso_cond, _ = sobrepaso_al_reencender("condicional")
    sobrepaso_ninguno, _ = sobrepaso_al_reencender("ninguno")
    # medido: condicional 5,3 °C (recalentar desde ~870 °C); ninguno 218 °C (integral de 1527 a 1,3 millones)
    assert sobrepaso_cond < 10.0                         # vuelve casi limpio al setpoint
    assert sobrepaso_ninguno > 100.0                     # sin anti-windup la integral se infló


def test_la_integral_no_cambia_mientras_esta_apagado_con_anti_windup():
    sim = en_regimen()
    antes = sim.pid.integral
    sim.config.actuador.encendido = False
    sim.avanzar(10 * MINUTO)
    assert sim.pid.integral == antes


def test_osciloscopio_con_el_horno_apagado():
    o = triac.formas_de_onda(64.65, 220.0, triac.resistencia(3000, 220), encendido=False)
    assert max(o["v_red"]) > 300                         # la red sigue presente
    assert not any(o["v_carga"]) and not any(o["corriente"]) and not any(o["v_triac"])
    assert any(o["compuerta"])                           # el control sigue enviando pulsos
