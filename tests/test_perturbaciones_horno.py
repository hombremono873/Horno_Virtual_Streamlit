"""Perturbaciones sobre el horno (puerta, red, ambiente) y ruido del termopar."""
import random
import statistics

import pytest

from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import Configuracion, ParametrosHorno, Perturbaciones
from simulador_horno.modelo import horno as modelo_horno
from simulador_horno.modelo.perturbaciones import (
    EventoAleatorio, factor_potencia_red, temperatura_ambiente,
)
from simulador_horno.simulacion.simulador import Simulador

HORAS = 4
T_SET = ParametrosHorno().T_SET


def regimen(**perturbaciones):
    """Corre HORAS con las perturbaciones dadas; devuelve (motor, T reales y errores de 2 h a 4 h)."""
    motor = Simulador(Configuracion(perturbaciones=Perturbaciones(**perturbaciones)), semilla=5)
    motor.avanzar(int(HORAS * 3600 / motor.config.horno.DT))
    h = motor.historial
    return motor, h.temperaturas[2 * 3600:], h.errores[2 * 3600:]


def test_derivada_ideal_es_la_formula_original():
    horno = ParametrosHorno()
    for T, u in ((30.0, 1.0), (512.3, 0.37), (1000.0, 0.764)):
        original = (1 / horno.TAU) * (horno.T_AMB - T) + horno.B * u
        assert modelo_horno.derivada(T, u, horno) == original      # bit a bit


def test_derivada_con_entorno_perturbado():
    horno = ParametrosHorno()
    T, u = 900.0, 0.5
    entorno = (40.0, 1 / limites.TAU_PUERTA, 0.9)   # ambiente, puerta abierta, red baja
    esperado = (1 / horno.TAU) * (40.0 - T) + horno.B * (u * 0.9) + (40.0 - T) / limites.TAU_PUERTA
    assert modelo_horno.derivada(T, u, horno, entorno) == pytest.approx(esperado)
    assert modelo_horno.derivada(T, u, horno, entorno) < modelo_horno.derivada(T, u, horno)


def test_sin_perturbaciones_la_temperatura_queda_plana():
    _, T, _ = regimen()
    assert max(T) - min(T) < 0.05


def test_puerta_abierta_hace_caer_la_temperatura_y_el_pid_la_recupera():
    motor, T, _ = regimen(puerta=True)
    assert motor.aperturas >= 3
    assert min(T) < T_SET - 20                       # caídas visibles
    assert abs(motor.T - T_SET) < 10 or motor.puerta_abierta


def test_tasa_de_aperturas_independiente_de_dt():
    def contar(dt, horas=200):
        rng, evento, n = random.Random(9), EventoAleatorio(), 0
        for k in range(int(horas * 3600 / dt)):
            _, nueva = evento.actualizar(k * dt, dt, limites.TASA_PUERTA_HORA, limites.DURACION_PUERTA, rng)
            n += nueva
        return n
    gruesa, fina = contar(5.0), contar(1.0)
    esperado = 200 * limites.TASA_PUERTA_HORA / (1 + limites.TASA_PUERTA_HORA * limites.DURACION_PUERTA / 3600)
    assert gruesa == pytest.approx(esperado, rel=0.2)
    assert fina == pytest.approx(esperado, rel=0.2)


def test_red_variable_hace_oscilar_la_temperatura_alrededor_del_setpoint():
    _, T, _ = regimen(red_variable=True)
    assert statistics.pstdev(T) > 0.5
    assert abs(statistics.fmean(T) - T_SET) < 1.0
    a = sum(limites.RED_AMPLITUDES)
    for t in range(0, 3600, 7):
        assert (1 - a) ** 2 <= factor_potencia_red(t, limites.RED_AMPLITUDES, limites.RED_PERIODOS) <= (1 + a) ** 2


def test_ambiente_variable_apenas_afecta_a_un_horno_controlado():
    assert temperatura_ambiente(900, 30.0, 10.0, 3600) == pytest.approx(40.0)   # cuarto de periodo
    _, T, _ = regimen(ambiente_variable=True)
    assert max(abs(x - T_SET) for x in T) < 0.5


def test_ruido_del_termopar_afecta_la_lectura_no_al_horno():
    _, T, errores = regimen(ruido_termopar=True)
    assert statistics.pstdev(errores) == pytest.approx(limites.RUIDO_TERMOPAR_SIGMA, rel=0.15)
    assert statistics.pstdev(T) < 0.3


def test_apagar_las_perturbaciones_devuelve_el_horno_ideal():
    base = Simulador()
    base.avanzar(20000)
    config = Configuracion(perturbaciones=Perturbaciones(puerta=True, red_variable=True,
                                                         ambiente_variable=True, ruido_termopar=True))
    otra = Simulador(config, semilla=5)
    otra.avanzar(20000)
    for atributo, _, _ in limites.PERTURBACIONES:
        setattr(config.perturbaciones, atributo, False)
    otra.reiniciar()
    otra.avanzar(20000)
    assert otra.T == base.T
