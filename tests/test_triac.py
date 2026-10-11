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


# ---- el triac dentro del simulador ---------------------------------------
from simulador_horno.configuracion.parametros import Configuracion, ParametrosActuador  # noqa: E402
from simulador_horno.simulacion.simulador import Simulador  # noqa: E402

DOS_HORAS = 72_000   # pasos de 0,1 s


def correr(**actuador):
    sim = Simulador(Configuracion(actuador=ParametrosActuador(**actuador)), semilla=3)
    sim.avanzar(DOS_HORAS)
    return sim


def test_modo_ideal_no_cambia_nada():
    sim = correr()
    h = sim.historial
    assert h.fracciones == h.potencias and all(math.isnan(a) for a in h.alfas)
    assert sim.metricas().sobrepaso_pct == pytest.approx(0.54, abs=0.05)


def test_compensado_entrega_lo_que_pide_el_pid():
    sim = correr(modo="triac_compensado")
    h = sim.historial
    minimo, maximo = triac.fraccion_potencia(170.0), triac.fraccion_potencia(10.0)
    for u, f in zip(h.potencias, h.fracciones):
        if minimo < u < maximo:                       # dentro de los límites físicos del disparo
            assert f == pytest.approx(u, abs=1e-9)
        elif u >= maximo:
            assert f == pytest.approx(maximo)         # el triac no llega al 100 %
    assert sim.alfa == pytest.approx(64.65, abs=0.2)  # régimen: ~76,4 % de potencia
    assert abs(sim.T - 1000.0) < 0.5


def test_ángulo_lineal_entrega_de_mas_y_el_pid_lo_compensa():
    lineal, ideal = correr(modo="triac_lineal"), correr()
    assert lineal.fraccion == pytest.approx(0.764, abs=0.01)   # el horno necesita lo mismo...
    assert lineal.u < ideal.u - 0.05                            # ...pero el PID pide menos
    assert abs(lineal.T - 1000.0) < 0.5                         # y aun así llega


def test_energia_y_potencia_en_vatios():
    sim = correr(modo="triac_compensado", potencia_nominal=3000.0)
    h = sim.historial
    assert max(h.potencias_w) <= 3000.0 and h.potencias_w[0] == pytest.approx(3000 * h.fracciones[0])
    energia = sum(p * 0.1 for p in h.potencias_w) / 3.6e6       # una muestra por segundo ≈ 10 pasos
    assert h.energias_kwh[-1] == pytest.approx(energia * 10, rel=0.01)
    assert 3.0 < sim.energia_j / 3.6e6 < 6.0                     # ~2 h con 3 kW, buena parte saturado


def test_dispersion_reproducible_con_semilla():
    a = correr(modo="triac_compensado", dispersion=0.5, resolucion=1.0)
    b = correr(modo="triac_compensado", dispersion=0.5, resolucion=1.0)
    assert a.historial.temperaturas == b.historial.temperaturas
    assert all(x == round(x) for x in a.historial.alfas)        # resolución de 1°
