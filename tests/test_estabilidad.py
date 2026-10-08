"""Estabilidad numérica con Δt grandes (numerico.estabilidad)."""
import pytest

from simulador_horno.configuracion.parametros import ParametrosHorno
from simulador_horno.numerico.estabilidad import (
    clasificar, estudiar, factor_amplificacion, limite_estabilidad,
)
from simulador_horno.numerico.integradores import METODOS

HORNO = ParametrosHorno()


@pytest.fixture(scope="module")
def resultado():
    return estudiar(HORNO)


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
        desv = [T - HORNO.T_AMB for T in tray.temperaturas[:4]]
        R = resultado.factores[(metodo, dt)]
        for a, b in zip(desv, desv[1:]):
            assert b / a == pytest.approx(R, rel=1e-9)


def test_comportamiento_observado_coincide_con_el_veredicto(resultado):
    for (metodo, dt), tray in resultado.trayectorias.items():
        inicial = abs(tray.temperaturas[0] - HORNO.T_AMB)
        final = abs(tray.temperaturas[-1] - HORNO.T_AMB)
        veredicto = resultado.veredicto(metodo, dt)
        if veredicto == "diverge":
            assert final > inicial
        else:
            assert final < inicial
        if veredicto == "oscila":   # cambia de lado de T_AMB en cada paso
            assert (tray.temperaturas[1] - HORNO.T_AMB) < 0 < (tray.temperaturas[2] - HORNO.T_AMB)


def test_casos_didacticos(resultado):
    """Los cuatro Δt muestran las cuatro situaciones que se quieren enseñar."""
    v = {(m, round(dt / HORNO.TAU, 1)): resultado.veredicto(m, dt) for (m, dt) in resultado.factores}
    assert all(v[(m, 0.5)] == "estable" for m in METODOS)
    assert v[("euler", 1.5)] == "oscila"
    assert v[("euler", 2.5)] == "diverge" and v[("rk4", 2.5)] == "estable"
    assert all(v[(m, 3.0)] == "diverge" for m in METODOS)


def test_no_altera_el_horno_del_usuario():
    horno = ParametrosHorno(DT=0.42)
    estudiar(horno)
    assert horno.DT == 0.42


def test_los_dt_escalan_con_la_tau_del_horno():
    r = estudiar(ParametrosHorno(TAU=1000))
    assert r.dts == (500.0, 1500.0, 2500.0, 3000.0)
    assert r.limites["euler"] == pytest.approx(2000.0, rel=1e-6)
