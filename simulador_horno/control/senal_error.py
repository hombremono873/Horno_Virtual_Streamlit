"""Construcción de la señal de error de control.

    error = T_SET - T   (+ perturbaciones activadas desde el menú)

Los conmutadores de perturbación viven en la capa de interfaz
(``interfaz.consola.formularios``); aquí solo se calcula el error.

Sin E/S: el comienzo de un impulso se INFORMA al llamador (el motor) y es
la interfaz quien decide cómo avisarlo (pitido, indicador en la tabla).
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.modelo.perturbaciones import get_ruido, perturbacion_total


def construir_error(t, T):
    """Error base (setpoint - temperatura) más las perturbaciones activas.

    Devuelve ``(error, impulso_nuevo)``; ``impulso_nuevo`` es True solo en
    el paso en que comienza un impulso.
    """
    error = vhorno.T_SET - T
    impulso_nuevo = False

    if vhorno.error_oscilante:
        error += get_ruido(t)

    if vhorno.flag_error:
        vhorno.delta_T, impulso_nuevo = perturbacion_total(
            t, vhorno.DT,
            tasa_hora=limites.TASA_IMPULSOS_HORA,
            duracion=limites.DURACION_IMPULSO,
            magnitud=limites.MAGNITUD_IMPULSO,
        )
        error += vhorno.delta_T

    return error, impulso_nuevo
