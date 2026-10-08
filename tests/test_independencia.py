"""Dos simuladores no se interfieren (requisito de la versión web).

Streamlit atiende a cada usuario en una sesión propia, en hilos del mismo
proceso: si el estado fuera global, lo que hace un estudiante cambiaría la
corrida de otro.
"""
import threading

from simulador_horno.configuracion.parametros import Configuracion, Perturbaciones
from simulador_horno.simulacion.simulador import Simulador

PASOS = 30_000   # 50 min simulados


def perturbada():
    return Configuracion(perturbaciones=Perturbaciones(
        error_oscilante=True, flag_error=True, ruido_termopar=True,
        puerta=True, red_variable=True, ambiente_variable=True))


def series(sim):
    h = sim.historial
    return (h.tiempos[:], h.temperaturas[:], h.errores[:], h.potencias[:], sim.impulsos, sim.aperturas)


def sola(config, semilla):
    sim = Simulador(config, semilla=semilla)
    sim.avanzar(PASOS)
    return series(sim)


def test_intercalados_dan_lo_mismo_que_por_separado():
    esperado_a, esperado_b = sola(perturbada(), 1), sola(perturbada(), 2)
    a, b = Simulador(perturbada(), semilla=1), Simulador(perturbada(), semilla=2)
    for _ in range(PASOS // 100):      # un poco cada uno, como dos sesiones a la vez
        a.avanzar(100)
        b.avanzar(100)
    assert series(a) == esperado_a
    assert series(b) == esperado_b
    assert esperado_a != esperado_b    # semillas distintas, corridas distintas


def test_en_hilos_dan_lo_mismo_que_por_separado():
    esperado = {s: sola(perturbada(), s) for s in (1, 2, 3)}
    obtenido = {}

    def correr(semilla):
        obtenido[semilla] = sola(perturbada(), semilla)

    hilos = [threading.Thread(target=correr, args=(s,)) for s in esperado]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert obtenido == esperado


def test_cambiar_un_parametro_no_afecta_al_otro():
    a, b = Simulador(), Simulador()
    a.config.pid.KP = 50
    a.config.horno.T_SET = 800.0
    a.config.perturbaciones.flag_error = True
    assert b.config.pid.KP == 200 and b.config.horno.T_SET == 1000.0
    assert not b.config.perturbaciones.flag_error
    a.avanzar(PASOS)
    b.avanzar(PASOS)
    assert series(b) == sola(Configuracion(), None)


def test_cada_configuracion_es_independiente():
    a, b = Configuracion(), Configuracion()
    assert a.horno is not b.horno and a.pid is not b.pid
    copia = a.copia()
    copia.horno.TAU = 1000
    assert a.horno.TAU == 3000


def test_misma_semilla_misma_corrida():
    assert sola(perturbada(), 7) == sola(perturbada(), 7)


def test_reiniciar_con_semilla_repite_la_corrida():
    sim = Simulador(perturbada(), semilla=9)
    sim.avanzar(PASOS)
    primera = series(sim)
    sim.reiniciar()
    sim.avanzar(PASOS)
    assert series(sim) == primera
