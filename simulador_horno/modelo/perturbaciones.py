"""Generación de perturbaciones sobre el sistema.

Incluye ruido aleatorio, una componente senoidal suave y un impulso
térmico probabilístico de signo alternante.

Todo se expresa en tiempo SIMULADO para que el resultado no dependa del
paso de integración ``dt``: el impulso se define por una tasa de eventos
por hora y se convierte a probabilidad por paso con

    p = 1 - exp(-tasa * dt)

(probabilidad de al menos un evento de Poisson en un intervalo ``dt``).
"""
import math
from random import random, uniform


def probabilidad_por_paso(tasa_hora, dt):
    """Probabilidad de que ocurra un evento en un paso ``dt`` (s)."""
    return 1.0 - math.exp(-(tasa_hora / 3600.0) * dt)


def reiniciar_impulso():
    """Olvida cualquier impulso en curso (se llama al empezar cada corrida)."""
    impulso_probabilistico.activo = False
    impulso_probabilistico.t_inicio = 0
    impulso_probabilistico.signo = 1


def impulso_probabilistico(t, dt, tasa_hora, duracion, magnitud):
    """Impulso que aparece con ``tasa_hora`` eventos/hora y dura ``duracion`` s.

    El signo se mantiene durante todo el impulso y se invierte de un
    impulso al siguiente (el primero es negativo). Devuelve
    ``(valor, activo, nuevo)``; ``nuevo`` es True solo en el paso en que
    el impulso comienza.
    """
    if impulso_probabilistico.activo:
        if t < impulso_probabilistico.t_inicio + duracion:
            return impulso_probabilistico.signo * abs(magnitud), True, False
        impulso_probabilistico.activo = False
        return 0, False, False

    if random() < probabilidad_por_paso(tasa_hora, dt):
        impulso_probabilistico.activo = True
        impulso_probabilistico.t_inicio = t
        impulso_probabilistico.signo *= -1
        return impulso_probabilistico.signo * abs(magnitud), True, True

    return 0, False, False


reiniciar_impulso()


def perturbacion_total(t, dt, tasa_hora, duracion, magnitud):
    """Perturbación total en el instante ``t``: ruido + senoide + impulso.

    Devuelve ``(total, impulso_nuevo)``.
    """
    ruido = uniform(-0.5, 1.5)
    senoide = 20 * math.sin(0.05 * t)
    impulso, _, nuevo = impulso_probabilistico(t, dt, tasa_hora, duracion, magnitud)
    total = ruido + senoide + impulso
    return total, nuevo


def get_ruido(t):
    """Ruido leve: senoide suave + ruido uniforme."""
    ruido = uniform(-0.5, 1.5)
    perturbacion = 20 * math.sin(0.05 * t)
    return perturbacion + ruido
