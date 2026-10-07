"""Física del horno: equilibrio a potencia plena y ganancia B derivada."""
import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.modelo.horno import simular_horno


def test_u_constante_converge_a_t_max_eq():
    vhorno.recalcular_B()
    T = vhorno.T_AMB
    pasos = int(10 * vhorno.TAU / vhorno.DT)   # 10 constantes de tiempo: e^-10 ≈ 4.5e-5
    for _ in range(pasos):
        T = simular_horno(T, 1.0)
    assert T == pytest.approx(vhorno.T_MAX_EQ, abs=0.5)


def test_b_por_defecto_es_fisicamente_razonable():
    vhorno.recalcular_B()
    assert vhorno.B == pytest.approx((1300 - 30) / 3000)
    assert vhorno.B < 1.0   # menos de 1 °C/s a potencia plena (antes: 100 °C/s)


@pytest.mark.parametrize("campo, valor", [("TAU", 1500), ("T_AMB", 20.0), ("T_MAX_EQ", 1600.0)])
def test_b_se_recalcula_al_cambiar_parametros(campo, valor):
    setattr(vhorno, campo, valor)
    B = vhorno.recalcular_B()
    assert B == pytest.approx((vhorno.T_MAX_EQ - vhorno.T_AMB) / vhorno.TAU)
    assert vhorno.B == B
