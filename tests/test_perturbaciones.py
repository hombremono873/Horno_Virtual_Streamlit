"""El impulso se define por tasa por hora simulada: su frecuencia no depende de DT."""
import math
import random

import pytest

from simulador_horno.modelo.perturbaciones import Impulso, Perturbador, probabilidad_por_paso

TASA = 360        # alta, para tener muchos eventos y una prueba rápida
DURACION = 3
HORAS = 10


def contar_impulsos(dt, semilla=2026):
    rng, impulso, eventos = random.Random(semilla), Impulso(), 0
    for k in range(int(HORAS * 3600 / dt)):
        _, _, nuevo = impulso.actualizar(k * dt, dt, TASA, DURACION, 80, rng)
        eventos += nuevo
    return eventos


def test_probabilidad_por_paso():
    assert probabilidad_por_paso(3600, 1.0) == pytest.approx(1 - math.exp(-1))
    assert probabilidad_por_paso(0, 0.1) == 0.0


def test_tasa_no_depende_de_dt():
    # Mientras un impulso dura no puede empezar otro: la tasa efectiva es
    # tasa / (1 + tasa * duracion), en eventos por hora.
    esperado = HORAS * TASA / (1 + TASA * DURACION / 3600)
    gruesa, fina = contar_impulsos(0.5), contar_impulsos(0.05)
    print(f"\n  Impulsos en {HORAS} h: DT=0.5 -> {gruesa}, DT=0.05 -> {fina}, esperado ≈ {esperado:.0f}")
    for n in (gruesa, fina):
        assert n == pytest.approx(esperado, rel=0.06)
    assert gruesa == pytest.approx(fina, rel=0.08)


def test_signo_constante_durante_el_impulso_y_alterno_entre_impulsos():
    rng, impulso = random.Random(7), Impulso()
    dt, signos_por_impulso, actual = 0.1, [], None
    for k in range(int(3 * 3600 / dt)):
        valor, activo, nuevo = impulso.actualizar(k * dt, dt, TASA, DURACION, 80, rng)
        if nuevo:
            actual = set()
            signos_por_impulso.append(actual)
        if activo:
            actual.add(math.copysign(1, valor))
    assert len(signos_por_impulso) > 10
    assert all(len(s) == 1 for s in signos_por_impulso)       # no oscila dentro del impulso
    signos = [next(iter(s)) for s in signos_por_impulso]
    assert signos[0] == -1                                      # el primero es negativo
    assert all(a == -b for a, b in zip(signos, signos[1:]))     # alternan entre impulsos


def test_misma_semilla_misma_secuencia_y_semillas_distintas_difieren():
    def serie(semilla):
        p = Perturbador(semilla)
        return [p.perturbacion_total(k * 0.5, 0.5, tasa_hora=TASA)[0] + p.ruido_termopar()
                for k in range(2000)]
    assert serie(42) == serie(42)
    assert serie(42) != serie(43)


def test_reiniciar_repite_la_corrida():
    p = Perturbador(5)
    primera = [p.ruido_oscilante(k) for k in range(100)]
    p.reiniciar(5)
    assert [p.ruido_oscilante(k) for k in range(100)] == primera


def test_dos_perturbadores_no_comparten_estado():
    """El impulso en curso y el generador son de cada instancia."""
    a, b = Perturbador(1), Perturbador(1)
    for k in range(5000):          # solo 'a' avanza: con tasa alta tendrá un impulso en curso
        a.perturbacion_total(k * 0.1, 0.1, tasa_hora=3600)
    assert b.impulso.activo is False and b.impulso.signo == 1
    assert b.rng.random() == Perturbador(1).rng.random()


def test_tasa_de_impulsos_configurable():
    from simulador_horno.configuracion.parametros import Configuracion, Perturbaciones
    from simulador_horno.simulacion.simulador import Simulador

    def impulsos(tasa):
        config = Configuracion(perturbaciones=Perturbaciones(flag_error=True, tasa_impulsos_hora=tasa))
        sim = Simulador(config, semilla=4)
        sim.avanzar(int(3 * 3600 / config.horno.DT))
        return sim.impulsos
    assert impulsos(0) == 0
    assert impulsos(60) > 3 * impulsos(6) > 0
