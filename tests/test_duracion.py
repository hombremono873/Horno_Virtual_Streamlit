"""Duración de la corrida: se detiene sola al completar las horas simuladas."""
import pytest

from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import (
    Configuracion, ParametrosHorno, ParametrosSimulacion,
)
from simulador_horno.simulacion.reloj import pasos_por_refresco, pasos_restantes
from simulador_horno.simulacion.simulador import Simulador


def simulador(horas, velocidad="x60", dt=0.1):
    return Simulador(Configuracion(horno=ParametrosHorno(DT=dt),
                                   simulacion=ParametrosSimulacion(velocidad=velocidad, duracion_horas=horas)))


def test_pasos_restantes():
    assert pasos_restantes(0.0, None, 0.1) is None             # sin límite
    assert pasos_restantes(0.0, 60.0, 0.1) == 600
    assert pasos_restantes(59.95, 60.0, 0.1) == 1
    assert pasos_restantes(60.0, 60.0, 0.1) == 0
    assert pasos_restantes(59.99999999, 60.0, 0.1) == 0        # redondeo al acumular t += dt
    assert pasos_restantes(75.0, 60.0, 0.1) == 0               # nunca negativo


def test_duracion_por_defecto():
    assert ParametrosSimulacion().duracion_horas == 2
    assert None in limites.DURACIONES_HORAS
    assert all(h is None or h * 3600 <= limites.MAX_MUESTRAS * limites.INTERVALO_MUESTREO
               for h in limites.DURACIONES_HORAS)   # cada corrida cabe entera en el historial


@pytest.mark.parametrize("velocidad", [v for v, f in limites.VELOCIDADES.items() if f is not None])
def test_se_detiene_exactamente_en_la_duracion(velocidad):
    """Refrescos de la velocidad elegida hasta terminar 15 min simulados."""
    sim = simulador(0.25, velocidad)
    factor, dt = limites.VELOCIDADES[velocidad], sim.config.horno.DT
    acumulado, refrescos = 0.0, 0
    while not sim.terminada:
        pasos, acumulado = pasos_por_refresco(factor, dt, limites.REFRESCO_HZ, acumulado)
        sim.avanzar_sin_pasarse(pasos)
        refrescos += 1
        assert refrescos < 20_000, "no terminó"
    assert sim.t == pytest.approx(900.0, abs=dt / 2)
    # una vez terminada ya no avanza aunque la interfaz siga refrescando
    assert sim.avanzar_sin_pasarse(1000) == 0 and sim.t == pytest.approx(900.0, abs=dt / 2)


def test_x600_tarda_lo_esperado_en_refrescos():
    # 15 min simulados a x600 = 1,5 s reales = 6 refrescos de 0,25 s
    sim = simulador(0.25, "x600")
    acumulado, refrescos = 0.0, 0
    while not sim.terminada:
        pasos, acumulado = pasos_por_refresco(600, sim.config.horno.DT, limites.REFRESCO_HZ, acumulado)
        sim.avanzar_sin_pasarse(pasos)
        refrescos += 1
    assert refrescos == 6


@pytest.mark.parametrize("dt", [0.1, 0.05, 0.3])
def test_completar_da_la_duracion_exacta(dt):
    sim = simulador(0.5, dt=dt)
    sim.completar()
    assert sim.terminada
    assert sim.t == pytest.approx(1800.0, abs=dt / 2)


def test_sin_limite_nunca_termina():
    sim = simulador(None)
    assert sim.pasos_restantes is None
    assert sim.avanzar_sin_pasarse(500) == 500 and not sim.terminada
    with pytest.raises(ValueError):
        sim.completar()


def test_la_corrida_completa_queda_en_el_historial():
    sim = simulador(8)      # la duración más larga
    sim.completar()
    assert sim.historial.tiempos[0] == pytest.approx(0.0)   # el arranque sigue ahí
    assert sim.historial.tiempos[-1] == pytest.approx(8 * 3600 - 1, abs=1)


def test_la_duracion_se_fija_al_reiniciar():
    sim = simulador(1)
    sim.config.simulacion.duracion_horas = 2      # cambiar a mitad de corrida no la alarga
    assert sim.duracion == 3600.0
    sim.reiniciar()
    assert sim.duracion == 7200.0
