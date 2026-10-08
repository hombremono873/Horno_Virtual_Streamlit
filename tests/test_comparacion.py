"""Comparación de métodos con la solución exacta (numerico.comparacion)."""
import pytest

from simulador_horno.configuracion.parametros import ParametrosHorno
from simulador_horno.numerico.comparacion import (
    DTS_COMPARACION, HORIZONTE, comparar, integrar, solucion_exacta,
)
from simulador_horno.numerico.integradores import EVALUACIONES, METODOS, ORDEN


@pytest.fixture(scope="module")
def resultado():
    return comparar()


def test_solucion_exacta():
    horno = ParametrosHorno()
    assert solucion_exacta(0.0, horno.T_AMB, horno) == pytest.approx(horno.T_AMB)
    assert solucion_exacta(1e9, horno.T_AMB, horno) == pytest.approx(horno.T_MAX_EQ)   # u = 1


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


def test_no_altera_el_horno_del_usuario():
    horno = ParametrosHorno(DT=0.37, TAU=2000)
    comparar(horno)
    tray = integrar("rk4", 60.0, horno)
    assert horno.DT == 0.37
    assert tray.dt == 60.0 and tray.tiempos[1] == 60.0


def test_usa_los_parametros_del_horno_recibido():
    """Con otra TAU la exacta cambia y el método la sigue."""
    rapido = ParametrosHorno(TAU=1000)
    tray = integrar("rk4", 15.0, rapido)
    assert tray.temperaturas[-1] == pytest.approx(solucion_exacta(HORIZONTE, rapido.T_AMB, rapido), abs=1e-3)
    assert tray.temperaturas[-1] > integrar("rk4", 15.0).temperaturas[-1]   # calienta más rápido
