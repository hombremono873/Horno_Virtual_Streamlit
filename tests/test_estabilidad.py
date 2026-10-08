"""Estabilidad numérica con Δt grandes (numerico.estabilidad)."""
import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.numerico.estabilidad import (
    clasificar, estudiar, factor_amplificacion, limite_estabilidad,
)
from simulador_horno.numerico.integradores import METODOS


@pytest.fixture(scope="module")
def resultado():
    return estudiar()


def test_factores_teoricos():
    tau = 3000.0
    assert factor_amplificacion("euler", 1.5 * tau, tau) == pytest.approx(-0.5)
    assert factor_amplificacion("heun", 1.5 * tau, tau) == pytest.approx(0.625)
    assert factor_amplificacion("rk4", 3.0 * tau, tau) == pytest.approx(1.375)


@pytest.mark.parametrize("metodo, limite_tau", [("euler", 2.0), ("heun", 2.0), ("rk4", 2.7853)])
def test_limites_de_estabilidad(metodo, limite_tau):
    assert limite_estabilidad(metodo, 3000.0) / 3000.0 == pytest.approx(limite_tau, abs=1e-4)


@pytest.mark.parametrize("R, esperado", [(0.5, "estable"), (-0.5, "oscila"), (-1.5, "diverge"), (1.2, "diverge")])
def test_clasificar(R, esperado):
    assert clasificar(R) == esperado


def test_el_codigo_amplifica_exactamente_por_R(resultado):
    """La razón entre desviaciones sucesivas de cada integrador real es R."""
    for (metodo, dt), tray in resultado.trayectorias.items():
        desv = [T - vhorno.T_AMB for T in tray.temperaturas[:4]]
        R = resultado.factores[(metodo, dt)]
        for a, b in zip(desv, desv[1:]):
            assert b / a == pytest.approx(R, rel=1e-9)


def test_comportamiento_observado_coincide_con_el_veredicto(resultado):
    for (metodo, dt), tray in resultado.trayectorias.items():
        inicial = abs(tray.temperaturas[0] - vhorno.T_AMB)
        final = abs(tray.temperaturas[-1] - vhorno.T_AMB)
        veredicto = resultado.veredicto(metodo, dt)
        if veredicto == "diverge":
            assert final > inicial
        else:
            assert final < inicial
        if veredicto == "oscila":   # cambia de lado de T_AMB en cada paso
            assert (tray.temperaturas[1] - vhorno.T_AMB) < 0 < (tray.temperaturas[2] - vhorno.T_AMB)


def test_casos_didacticos(resultado):
    """Los cuatro Δt muestran las cuatro situaciones que se quieren enseñar."""
    v = {(m, round(dt / vhorno.TAU, 1)): resultado.veredicto(m, dt) for (m, dt) in resultado.factores}
    assert all(v[(m, 0.5)] == "estable" for m in METODOS)
    assert v[("euler", 1.5)] == "oscila"
    assert v[("euler", 2.5)] == "diverge" and v[("rk4", 2.5)] == "estable"
    assert all(v[(m, 3.0)] == "diverge" for m in METODOS)


def test_no_altera_el_dt_del_usuario():
    vhorno.DT = 0.42
    estudiar()
    assert vhorno.DT == 0.42
