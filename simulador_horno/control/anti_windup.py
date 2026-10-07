"""Anti-windup: recorte del término integral del PID.

Cuando la integral supera ``limites.UMBRAL_INTEGRAL`` se escala por el
factor ``parametros_pid.restringir_integral`` (configurable en el menú, opción 5).
"""
from simulador_horno.configuracion import parametros_pid as vpid


def minimizar_integral(integral):
    r = vpid.restringir_integral
    return max(min(integral, integral * r), -integral * r)
