"""Compresión del tiempo de ejecución (sin E/S ni dependencias de reloj).

La física no se toca: ``DT`` queda fijo. Lo que cambia con la velocidad
es cuántos pasos de simulación se ejecutan en cada refresco de pantalla:

    N = factor / (REFRESCO_HZ * DT)

de modo que tiempo simulado / tiempo real = factor.
"""


def pasos_por_refresco(factor, dt, hz, acumulado=0.0):
    """Pasos a ejecutar en este refresco y fracción sobrante.

    La parte fraccionaria se acumula entre refrescos para que factores
    pequeños (x1 -> 2.5 pasos por refresco) también sean exactos.
    Devuelve ``(pasos, acumulado)``.
    """
    acumulado += factor / (hz * dt)
    pasos = int(acumulado + 1e-9)   # tolerancia a errores de redondeo
    return pasos, acumulado - pasos

