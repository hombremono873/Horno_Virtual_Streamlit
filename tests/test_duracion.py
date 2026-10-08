"""Duración de la corrida: se detiene sola al completar las horas simuladas.

Usa el bucle real de ``Simulador._avanzar_refresco`` (sin abrir la ventana:
el monitor solo se crea en ``ejecutar``).
"""
import time

import pytest

from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_simulacion as vsim
from simulador_horno.simulacion.reloj import pasos_restantes
from simulador_horno.simulacion.simulador import Simulador

PERIODO = 1.0 / limites.REFRESCO_HZ


def test_pasos_restantes():
    assert pasos_restantes(0.0, None, 0.1) is None             # sin límite
    assert pasos_restantes(0.0, 60.0, 0.1) == 600
    assert pasos_restantes(59.95, 60.0, 0.1) == 1
    assert pasos_restantes(60.0, 60.0, 0.1) == 0
    assert pasos_restantes(59.99999999, 60.0, 0.1) == 0        # redondeo al acumular t += dt
    assert pasos_restantes(75.0, 60.0, 0.1) == 0               # nunca negativo


def test_duracion_por_defecto():
    assert vsim.duracion_horas == 2
    assert None in limites.DURACIONES_HORAS
    assert all(h is None or h * 3600 <= limites.MAX_MUESTRAS * limites.INTERVALO_MUESTREO
               for h in limites.DURACIONES_HORAS)   # cada corrida cabe entera en el historial


@pytest.mark.parametrize("velocidad", list(limites.VELOCIDADES))
def test_se_detiene_exactamente_en_la_duracion(velocidad):
    vsim.velocidad, vsim.duracion_horas = velocidad, 0.25     # 15 min simulados
    sim = Simulador()
    refrescos = 0
    while not sim.terminada:
        sim._avanzar_refresco(time.monotonic(), PERIODO)
        refrescos += 1
        assert refrescos < 10_000, "no terminó"
    assert sim.motor.t == pytest.approx(900.0, abs=vhorno.DT / 2)
    # una vez terminada ya no avanza aunque el bucle siga refrescando
    t_final = sim.motor.t
    for _ in range(5):
        sim._avanzar_refresco(time.monotonic(), PERIODO)
    assert sim.motor.t == t_final


def test_x600_tarda_lo_esperado_en_refrescos():
    # 15 min simulados a x600 = 1,5 s reales = 6 refrescos de 0,25 s
    vsim.velocidad, vsim.duracion_horas = "x600", 0.25
    sim = Simulador()
    refrescos = 0
    while not sim.terminada:
        sim._avanzar_refresco(time.monotonic(), PERIODO)
        refrescos += 1
    assert refrescos == 6


def test_sin_limite_nunca_termina():
    vsim.velocidad, vsim.duracion_horas = "x600", None
    sim = Simulador()
    for _ in range(20):
        sim._avanzar_refresco(time.monotonic(), PERIODO)
    assert not sim.terminada and sim.motor.t > 0


def test_la_corrida_completa_queda_en_el_historial():
    vsim.velocidad, vsim.duracion_horas = "máxima", 8      # la duración más larga
    sim = Simulador()
    while not sim.terminada:
        sim._avanzar_refresco(time.monotonic(), PERIODO)
    assert sim.motor.historial.tiempos[0] == pytest.approx(0.0)   # el arranque sigue ahí
