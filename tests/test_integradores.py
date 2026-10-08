"""Métodos numéricos: Euler, Heun y RK4 frente a la solución exacta.

Con u constante la ecuación del horno tiene solución analítica:

    T(t) = T_eq + (T0 - T_eq)·e^(-t/TAU),   T_eq = T_AMB + B·u·TAU
"""
import math

import pytest

from simulador_horno.configuracion.parametros import (
    Configuracion, ParametrosHorno, ParametrosSimulacion,
)
from simulador_horno.numerico.integradores import METODOS, NOMBRES
from simulador_horno.simulacion.simulador import Simulador

ORDEN = {"euler": 1, "heun": 2, "rk4": 4}
HORIZONTE = 3600.0   # s simulados


def solucion_exacta(t, horno, u=1.0):
    T_eq = horno.T_AMB + horno.B * u * horno.TAU
    return T_eq + (horno.T_AMB - T_eq) * math.exp(-t / horno.TAU)


def error_global(metodo, dt, u=1.0):
    """|T_numérica - T_exacta| al final del horizonte, integrando con paso dt."""
    horno = ParametrosHorno(DT=dt)
    T = horno.T_AMB
    for _ in range(int(round(HORIZONTE / dt))):
        T = METODOS[metodo](T, u, horno)
    return abs(T - solucion_exacta(HORIZONTE, horno, u))


def test_cada_metodo_tiene_nombre():
    assert set(METODOS) == set(NOMBRES) == set(ORDEN)


@pytest.mark.parametrize("metodo", list(METODOS))
def test_u_constante_converge_a_t_max_eq(metodo):
    horno = ParametrosHorno(DT=1.0)
    T = horno.T_AMB
    for _ in range(int(10 * horno.TAU)):     # 10 constantes de tiempo
        T = METODOS[metodo](T, 1.0, horno)
    assert T == pytest.approx(horno.T_MAX_EQ, abs=0.5)


def test_metodos_ordenados_por_precision():
    errores = {m: error_global(m, dt=60.0) for m in METODOS}
    print("\n  Error tras 1 h con Δt = 60 s: " + ", ".join(f"{NOMBRES[m]} {e:.2e} °C" for m, e in errores.items()))
    assert errores["euler"] > errores["heun"] > errores["rk4"]


@pytest.mark.parametrize("metodo", list(METODOS))
def test_orden_de_convergencia(metodo):
    # Al dividir Δt a la mitad, el error global de un método de orden p se
    # divide por ~2^p; el orden observado es log2(e(Δt) / e(Δt/2)).
    e_grueso, e_fino = error_global(metodo, 120.0), error_global(metodo, 60.0)
    orden = math.log2(e_grueso / e_fino)
    print(f"\n  {NOMBRES[metodo]}: orden observado {orden:.2f} (teórico {ORDEN[metodo]})")
    assert orden == pytest.approx(ORDEN[metodo], abs=0.15)


def simulador(metodo, dt=0.1):
    return Simulador(Configuracion(horno=ParametrosHorno(DT=dt),
                                   simulacion=ParametrosSimulacion(metodo=metodo)))


def test_euler_por_defecto():
    assert ParametrosSimulacion().metodo == "euler"
    assert Simulador().metodo == "euler"


@pytest.mark.parametrize("metodo", list(METODOS))
def test_simulador_usa_el_metodo_elegido_y_alcanza_el_setpoint(metodo):
    sim = simulador(metodo)
    assert sim.metodo == metodo
    sim.avanzar(int(3 * 3600 / sim.config.horno.DT))
    assert sim.T == pytest.approx(sim.config.horno.T_SET, abs=0.5)


def test_metodos_dan_curvas_distintas_con_dt_grande():
    # Con Δt = 30 s Euler se aparta claramente de RK4 durante la subida.
    finales = {}
    for metodo in ("euler", "rk4"):
        sim = simulador(metodo, dt=30.0)
        sim.avanzar(int(20 * 60 / 30.0))   # 20 min de subida a potencia plena
        finales[metodo] = sim.T
    assert abs(finales["euler"] - finales["rk4"]) > 0.5


def test_el_metodo_se_fija_al_reiniciar():
    sim = simulador("euler")
    sim.config.simulacion.metodo = "rk4"
    assert sim.metodo == "euler"
    sim.reiniciar()
    assert sim.metodo == "rk4"
