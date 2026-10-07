"""El impulso se define por tasa por hora simulada: su frecuencia no depende de DT."""
import math
import random

import pytest

from simulador_horno.modelo.perturbaciones import (
    impulso_probabilistico, probabilidad_por_paso, reiniciar_impulso,
)

TASA = 360        # alta, para tener muchos eventos y una prueba rápida
DURACION = 3
HORAS = 10


def contar_impulsos(dt, semilla=2026):
    random.seed(semilla)
    reiniciar_impulso()
    eventos = 0
    for k in range(int(HORAS * 3600 / dt)):
        _, _, nuevo = impulso_probabilistico(k * dt, dt, TASA, DURACION, 80)
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
    random.seed(7)
    reiniciar_impulso()
    dt, signos_por_impulso, actual = 0.1, [], None
    for k in range(int(3 * 3600 / dt)):
        valor, activo, nuevo = impulso_probabilistico(k * dt, dt, TASA, DURACION, 80)
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
