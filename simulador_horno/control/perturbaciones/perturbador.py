"""Generación de perturbaciones sobre el sistema.

Incluye ruido aleatorio, una componente senoidal suave y un impulso
térmico probabilístico de signo alternante.
"""
import math
from random import random, uniform


def impulso_probabilistico(t, probabilidad, duracion, magnitud):
    """Impulso que se activa con cierta probabilidad y dura ``duracion`` segundos.

    Mientras está activo alterna el signo en cada llamada. Devuelve
    ``(valor, activo)``.
    """
    if not hasattr(impulso_probabilistico, "activo"):
        impulso_probabilistico.activo = False
        impulso_probabilistico.t_inicio = 0
        impulso_probabilistico.signo = 1

    if impulso_probabilistico.activo:
        if t < impulso_probabilistico.t_inicio + duracion:
            impulso_probabilistico.signo *= -1
            return impulso_probabilistico.signo * abs(magnitud), True
        impulso_probabilistico.activo = False
        return 0, False

    if random() < probabilidad:
        impulso_probabilistico.activo = True
        impulso_probabilistico.t_inicio = t
        impulso_probabilistico.signo = -1
        return impulso_probabilistico.signo * abs(magnitud), True

    return 0, False


def perturbacion_total(t, probabilidad=0.05, duracion=3, magnitud=-40):
    """Perturbación total en el instante ``t``: ruido + senoide + impulso."""
    ruido = uniform(-0.5, 1.5)
    senoide = 20 * math.sin(0.05 * t)
    impulso, activo = impulso_probabilistico(t, probabilidad, duracion, magnitud)
    total = ruido + senoide + impulso
    return total, activo


def get_ruido(t):
    """Ruido leve: senoide suave + ruido uniforme."""
    ruido = uniform(-0.5, 1.5)
    perturbacion = 20 * math.sin(0.05 * t)
    return perturbacion + ruido
