"""Saturación de la señal de control del PID."""
from simulador_horno.configuracion import limites


def escalar_u(u, u_max=limites.U_MAX, tope=1.0):
    """Normaliza ``u`` por ``u_max`` y lo satura al rango [0, tope].

    ``tope`` es el límite de potencia que fija el usuario (1 = sin límite).

    Un horno eléctrico solo puede calentar: no hay potencia negativa
    (enfriamiento activo), por eso el mínimo es 0 y no -1.
    """
    if u_max <= 0:
        raise ValueError("u_max debe ser mayor que cero")
    u_escalado = u / u_max
    return max(0.0, min(tope, u_escalado))
