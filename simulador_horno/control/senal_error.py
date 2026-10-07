"""Construcción de la señal de error de control.

    error = T_SET - T   (+ perturbaciones activadas desde el menú)

Los conmutadores de perturbación viven en la capa de interfaz
(``interfaz.consola.formularios``); aquí solo se calcula el error.

Nota de arquitectura: la alarma sonora del impulso se dispara aquí para
reproducir el comportamiento original. En una iteración futura conviene
que sea la capa de simulación quien decida notificar el evento.
"""
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.modelo.perturbaciones import get_ruido, perturbacion_total
from simulador_horno.interfaz.alarmas import sonora


def construir_error(t, T):
    """Error base (setpoint - temperatura) más las perturbaciones activas."""
    error = vhorno.T_SET - T

    if vhorno.error_oscilante:
        error += get_ruido(t)

    if vhorno.flag_error:
        vhorno.delta_T, hay_impulso = perturbacion_total(
            t, probabilidad=0.02, duracion=3, magnitud=80
        )
        sonora.alarma_impulso(hay_impulso)
        error += vhorno.delta_T

    return error
