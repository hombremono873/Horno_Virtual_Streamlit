"""Construcción de la señal de error de control.

    error = T_SET - T   (+ perturbaciones de la medición activas)

Sin E/S ni estado propio: los conmutadores llegan en ``perturbaciones`` y
los números aleatorios del ``perturbador`` de la corrida. El comienzo de
un impulso se INFORMA al llamador (el simulador) y es la interfaz quien
decide cómo avisarlo.
"""


def construir_error(t, T, T_set, dt, perturbaciones, perturbador):
    """Error base (setpoint - temperatura) más las perturbaciones activas.

    Devuelve ``(error, impulso_nuevo)``; ``impulso_nuevo`` es True solo en
    el paso en que comienza un impulso.
    """
    error = T_set - T
    impulso_nuevo = False

    if perturbaciones.ruido_termopar:   # el termopar lee T + ruido -> el error baja en ese ruido
        error -= perturbador.ruido_termopar()

    if perturbaciones.error_oscilante:
        error += perturbador.ruido_oscilante(t)

    if perturbaciones.flag_error:
        delta, impulso_nuevo = perturbador.perturbacion_total(t, dt, perturbaciones.tasa_impulsos_hora)
        error += delta

    return error, impulso_nuevo
