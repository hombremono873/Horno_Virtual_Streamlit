"""Saturación de la señal de control del PID."""
from simulador_horno.configuracion import limites


def escalar_u(u, u_max=limites.U_MAX):
    """Normaliza ``u`` por ``u_max`` y lo satura al rango [-1, 1]."""
    if u_max <= 0:
        raise ValueError("u_max debe ser mayor que cero")
    u_escalado = u / u_max
    return max(-1.0, min(1.0, u_escalado))
