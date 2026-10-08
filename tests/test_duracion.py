"""Duración de la corrida: pasos que faltan para completar las horas simuladas."""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_simulacion as vsim
from simulador_horno.simulacion.reloj import pasos_restantes


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
