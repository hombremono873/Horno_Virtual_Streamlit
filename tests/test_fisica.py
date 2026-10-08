"""Física del horno: equilibrio a potencia plena y ganancia B derivada."""
import pytest

from simulador_horno.configuracion.parametros import ParametrosHorno
from simulador_horno.modelo.horno import simular_horno


def test_u_constante_converge_a_t_max_eq():
    horno = ParametrosHorno()
    T = horno.T_AMB
    pasos = int(10 * horno.TAU / horno.DT)   # 10 constantes de tiempo: e^-10 ≈ 4.5e-5
    for _ in range(pasos):
        T = simular_horno(T, 1.0, horno)
    assert T == pytest.approx(horno.T_MAX_EQ, abs=0.5)


def test_b_por_defecto_es_fisicamente_razonable():
    horno = ParametrosHorno()
    assert horno.B == pytest.approx((1300 - 30) / 3000)
    assert horno.B < 1.0   # menos de 1 °C/s a potencia plena (antes: 100 °C/s)


@pytest.mark.parametrize("campo, valor", [("TAU", 1500), ("T_AMB", 20.0), ("T_MAX_EQ", 1600.0)])
def test_b_se_recalcula_al_cambiar_parametros(campo, valor):
    horno = ParametrosHorno()
    setattr(horno, campo, valor)
    assert horno.B == pytest.approx((horno.T_MAX_EQ - horno.T_AMB) / horno.TAU)


def test_b_con_tau_nula_no_divide_por_cero():
    assert ParametrosHorno(TAU=0).B == pytest.approx((1300 - 30) / 1e-6)
