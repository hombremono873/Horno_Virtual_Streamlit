"""Triac: curva de potencia, inversión numérica (bisección y Newton) y disparo real."""
import math
import random

import pytest

from simulador_horno.modelo import triac

VALORES_U = [0.001, 0.01, 0.05, 0.25, 0.5, 0.764, 0.9, 0.99, 0.999]


def test_curva_en_puntos_conocidos():
    assert triac.fraccion_potencia(0) == pytest.approx(1.0)
    assert triac.fraccion_potencia(90) == pytest.approx(0.5)
    assert triac.fraccion_potencia(180) == pytest.approx(0.0, abs=1e-15)
    assert triac.fraccion_potencia(10) == pytest.approx(0.9989, abs=1e-4)
    assert triac.fraccion_potencia(170) == pytest.approx(0.0011, abs=1e-4)


def test_curva_decreciente_y_derivada_correcta():
    angulos = [i * 0.5 for i in range(361)]
    valores = [triac.fraccion_potencia(a) for a in angulos]
    assert all(a > b for a, b in zip(valores, valores[1:]))
    for a in (5.0, 45.0, 90.0, 120.0, 175.0):   # contra diferencia central
        h = 1e-5
        numerica = (triac.fraccion_potencia(a + h) - triac.fraccion_potencia(a - h)) / (2 * h)
        assert triac.derivada_fraccion(a) == pytest.approx(numerica, rel=1e-6)
    assert triac.derivada_fraccion(0) == 0.0 and triac.derivada_fraccion(180) == pytest.approx(0.0, abs=1e-30)


def test_el_angulo_lineal_entrega_otra_potencia():
    """El ejemplo del artículo: el PID pide 76,4 % y el ángulo lineal da 92,3 %."""
    alfa = triac.angulo_lineal(0.764)
    assert alfa == pytest.approx(42.48)
    assert triac.fraccion_potencia(alfa) == pytest.approx(0.923, abs=1e-3)


@pytest.mark.parametrize("metodo", ["newton", "biseccion"])
@pytest.mark.parametrize("u", VALORES_U)
def test_ida_y_vuelta(metodo, u):
    alfa, iteraciones = triac.angulo_compensado(u, metodo)
    assert 0.0 < alfa < 180.0 and iteraciones > 0
    assert triac.fraccion_potencia(alfa) == pytest.approx(u, abs=1e-9)


def test_ejemplo_76_por_ciento():
    alfa, _ = triac.angulo_por_newton(0.764)
    assert alfa == pytest.approx(64.65, abs=0.01)


def test_newton_converge_en_menos_iteraciones_que_biseccion():
    for u in VALORES_U:
        _, it_newton = triac.angulo_por_newton(u)
        _, it_biseccion = triac.angulo_por_biseccion(u)
        assert it_newton < it_biseccion, u
    assert triac.angulo_por_biseccion(0.5)[1] == math.ceil(math.log2(180 / triac.TOLERANCIA))


def test_extremos():
    for metodo in ("newton", "biseccion"):
        assert triac.angulo_compensado(0.0, metodo) == (triac.ALFA_APAGADO, 0)
        assert triac.angulo_compensado(1.0, metodo) == (0.0, 0)
        assert triac.angulo_compensado(-3.0, metodo)[0] == triac.ALFA_APAGADO
    with pytest.raises(ValueError):
        triac.angulo_compensado(0.5, "magia")


def test_disparo_real():
    assert triac.disparo_real(180.0, 10, 170) == 180.0                  # apagado
    assert triac.disparo_real(3.0, 10, 170) == 10.0                     # límite físico
    assert triac.disparo_real(64.65, 10, 170, resolucion=1.0) == 65.0   # resolución del temporizador
    rng_a, rng_b = random.Random(5), random.Random(5)
    a = [triac.disparo_real(64.65, 10, 170, 0.0, 0.5, rng_a) for _ in range(500)]
    b = [triac.disparo_real(64.65, 10, 170, 0.0, 0.5, rng_b) for _ in range(500)]
    assert a == b                                                       # misma semilla, mismo disparo
    media = sum(a) / len(a)
    assert media == pytest.approx(64.65, abs=0.1) and max(a) - min(a) > 1.0


def test_unidades_electricas():
    R = triac.resistencia(3000.0, 220.0)
    assert R == pytest.approx(16.133, abs=1e-3)
    assert triac.potencia_electrica(0.0, 220.0, R) == pytest.approx(3000.0)
    assert triac.potencia_electrica(90.0, 220.0, R) == pytest.approx(1500.0)
    assert triac.voltaje_rms(90.0, 220.0) == pytest.approx(220.0 / math.sqrt(2))
    assert triac.energia_kwh(3.6e6) == 1.0
