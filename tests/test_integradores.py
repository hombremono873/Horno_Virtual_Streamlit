"""Métodos numéricos: Euler, Heun y RK4 frente a la solución exacta.

Con u constante la ecuación del horno tiene solución analítica:

    T(t) = T_eq + (T0 - T_eq)·e^(-t/TAU),   T_eq = T_AMB + B·u·TAU
"""
import math

import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_simulacion as vsim
from simulador_horno.numerico.integradores import METODOS, NOMBRES
from simulador_horno.simulacion.motor import Motor

ORDEN = {"euler": 1, "heun": 2, "rk4": 4}
HORIZONTE = 3600.0   # s simulados


def solucion_exacta(t, u=1.0):
    T_eq = vhorno.T_AMB + vhorno.B * u * vhorno.TAU
    return T_eq + (vhorno.T_AMB - T_eq) * math.exp(-t / vhorno.TAU)


def error_global(metodo, dt, u=1.0):
    """|T_numérica - T_exacta| al final del horizonte, integrando con paso dt."""
    vhorno.DT = dt
    vhorno.recalcular_B()
    T = vhorno.T_AMB
    for _ in range(int(round(HORIZONTE / dt))):
        T = METODOS[metodo](T, u)
    return abs(T - solucion_exacta(HORIZONTE, u))


def test_cada_metodo_tiene_nombre():
    assert set(METODOS) == set(NOMBRES) == set(ORDEN)


@pytest.mark.parametrize("metodo", list(METODOS))
def test_u_constante_converge_a_t_max_eq(metodo):
    vhorno.DT = 1.0
    vhorno.recalcular_B()
    T = vhorno.T_AMB
    for _ in range(int(10 * vhorno.TAU)):     # 10 constantes de tiempo
        T = METODOS[metodo](T, 1.0)
    assert T == pytest.approx(vhorno.T_MAX_EQ, abs=0.5)


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


def test_euler_por_defecto():
    assert vsim.metodo == "euler"
    assert Motor().metodo == "euler"


@pytest.mark.parametrize("metodo", list(METODOS))
def test_motor_usa_el_metodo_elegido_y_alcanza_el_setpoint(metodo):
    vsim.metodo = metodo
    motor = Motor()
    assert motor.metodo == metodo
    motor.avanzar(int(3 * 3600 / vhorno.DT))
    assert motor.T == pytest.approx(vhorno.T_SET, abs=0.5)


def test_metodos_dan_curvas_distintas_con_dt_grande():
    # Con Δt = 30 s Euler se aparta claramente de RK4 durante la subida.
    finales = {}
    for metodo in ("euler", "rk4"):
        vsim.metodo, vhorno.DT = metodo, 30.0
        motor = Motor()
        motor.avanzar(int(20 * 60 / vhorno.DT))   # 20 min de subida a potencia plena
        finales[metodo] = motor.T
    assert abs(finales["euler"] - finales["rk4"]) > 0.5
