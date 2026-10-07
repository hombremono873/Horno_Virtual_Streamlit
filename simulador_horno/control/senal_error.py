"""Construcción de la señal de error de control.

    error = T_SET - T   (+ perturbaciones activadas desde el menú)

Los conmutadores de perturbación viven en la capa de interfaz
(``interfaz.consola.formularios``); aquí solo se calcula el error.

Nota de arquitectura: la alarma sonora del impulso se dispara aquí para
reproducir el comportamiento original. En una iteración futura conviene
que sea la capa de simulación quien decida notificar el evento.
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.interfaz.alarmas import sonora
from simulador_horno.modelo.perturbaciones import get_ruido, perturbacion_total


def construir_error(t, T):
    """Error base (setpoint - temperatura) más las perturbaciones activas."""
    error = vhorno.T_SET - T

    if vhorno.error_oscilante:
        error += get_ruido(t)

    if vhorno.flag_error:
        vhorno.delta_T, impulso_nuevo = perturbacion_total(
            t, vhorno.DT,
            tasa_hora=limites.TASA_IMPULSOS_HORA,
            duracion=limites.DURACION_IMPULSO,
            magnitud=limites.MAGNITUD_IMPULSO,
        )
        sonora.alarma_impulso(impulso_nuevo)   # suena una vez, al empezar el impulso
        error += vhorno.delta_T

    return error
