"""Compresión de tiempo: N pasos por refresco con relación simulado/real = factor."""
import pytest

from simulador_horno.configuracion import limites, parametros_simulacion
from simulador_horno.simulacion.reloj import pasos_por_refresco

FACTORES = [f for f in limites.VELOCIDADES.values() if f is not None]


@pytest.mark.parametrize("factor", FACTORES)
@pytest.mark.parametrize("dt", [0.1, 0.05, 0.3])
def test_relacion_simulado_real_igual_al_factor(factor, dt):
    hz = limites.REFRESCO_HZ
    segundos_reales = 60
    acumulado, pasos_totales = 0.0, 0
    for _ in range(segundos_reales * hz):
        pasos, acumulado = pasos_por_refresco(factor, dt, hz, acumulado)
        assert pasos >= 0
        pasos_totales += pasos
    tiempo_simulado = pasos_totales * dt
    # exacto salvo, como mucho, un paso pendiente en el acumulador
    assert abs(tiempo_simulado - factor * segundos_reales) <= dt + 1e-9


def test_x1_reparte_la_fraccion():
    # x1 con DT = 0.1 y 4 Hz -> 2.5 pasos por refresco: alterna 2 y 3
    acumulado, pasos = 0.0, []
    for _ in range(4):
        n, acumulado = pasos_por_refresco(1, 0.1, 4, acumulado)
        pasos.append(n)
    assert sorted(pasos) == [2, 2, 3, 3]


def test_velocidades_disponibles():
    assert parametros_simulacion.velocidad == "x60"
    assert list(limites.VELOCIDADES) == ["x1", "x10", "x60", "x600", "máxima"]
    assert limites.VELOCIDADES["máxima"] is None
