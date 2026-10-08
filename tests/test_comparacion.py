"""Comparación de métodos con la solución exacta (numerico.comparacion)."""
import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.numerico.comparacion import (
    DTS_COMPARACION, HORIZONTE, comparar, integrar, solucion_exacta,
)
from simulador_horno.numerico.integradores import EVALUACIONES, METODOS, ORDEN


@pytest.fixture(scope="module")
def resultado():
    return comparar()


def test_solucion_exacta():
    vhorno.recalcular_B()
    assert solucion_exacta(0.0, vhorno.T_AMB) == pytest.approx(vhorno.T_AMB)
    assert solucion_exacta(1e9, vhorno.T_AMB) == pytest.approx(vhorno.T_MAX_EQ)   # u = 1


@pytest.mark.parametrize("metodo", list(METODOS))
def test_orden_observado_coincide_con_el_teorico(resultado, metodo):
    for orden in resultado.ordenes[metodo]:
        assert orden == pytest.approx(ORDEN[metodo], abs=0.1)


@pytest.mark.parametrize("dt", DTS_COMPARACION)
def test_mayor_orden_menor_error(resultado, dt):
    assert resultado.error("euler", dt) > resultado.error("heun", dt) > resultado.error("rk4", dt)


@pytest.mark.parametrize("metodo", list(METODOS))
def test_el_error_baja_al_reducir_dt(resultado, metodo):
    errores = [resultado.error(metodo, dt) for dt in DTS_COMPARACION]
    assert errores == sorted(errores, reverse=True)


def test_costo_en_evaluaciones(resultado):
    for (metodo, dt), tray in resultado.trayectorias.items():
        assert tray.evaluaciones == round(HORIZONTE / dt) * EVALUACIONES[metodo]
    # RK4 con pocas evaluaciones supera a Euler con muchas
    rk4_barato = resultado.trayectorias[("rk4", max(DTS_COMPARACION))]
    euler_caro = resultado.trayectorias[("euler", min(DTS_COMPARACION))]
    assert rk4_barato.evaluaciones < euler_caro.evaluaciones
    assert rk4_barato.error_maximo < euler_caro.error_maximo


def test_no_altera_el_dt_del_usuario():
    vhorno.DT = 0.37
    comparar()
    integrar("rk4", 60.0)
    assert vhorno.DT == 0.37


def test_restaura_dt_aunque_falle(monkeypatch):
    from simulador_horno.numerico import comparacion

    def falla(T, u):
        raise RuntimeError("fallo simulado")

    monkeypatch.setitem(comparacion.METODOS, "euler", falla)
    vhorno.DT = 0.25
    with pytest.raises(RuntimeError):
        integrar("euler", 60.0)
    assert vhorno.DT == 0.25
