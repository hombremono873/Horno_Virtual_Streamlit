"""Compresión del tiempo de ejecución y fin de la corrida (sin E/S ni reloj).

La física no se toca: ``DT`` queda fijo. Lo que cambia con la velocidad
es cuántos pasos de simulación se ejecutan en cada refresco de pantalla:

    N = factor / (REFRESCO_HZ * DT)

de modo que tiempo simulado / tiempo real = factor.
"""
import math


def pasos_por_refresco(factor, dt, hz, acumulado=0.0):
    """Pasos a ejecutar en este refresco y fracción sobrante.

    La parte fraccionaria se acumula entre refrescos para que factores
    pequeños (x1 -> 2.5 pasos por refresco) también sean exactos.
    Devuelve ``(pasos, acumulado)``.
    """
    acumulado += factor / (hz * dt)
    pasos = int(acumulado + 1e-9)   # tolerancia a errores de redondeo
    return pasos, acumulado - pasos


def pasos_restantes(t, duracion, dt):
    """Pasos que faltan para completar ``duracion`` segundos simulados.

    ``None`` si la corrida no tiene límite. La tolerancia evita un paso de
    más por errores de redondeo al acumular ``t += dt``.
    """
    if duracion is None:
        return None
    return max(0, math.ceil((duracion - t) / dt - 1e-6))
