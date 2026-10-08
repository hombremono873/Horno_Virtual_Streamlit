"""Conversión de la señal de control ``u`` (0..1) a un ángulo de conducción.

Un ``u`` alto -> ángulo de disparo pequeño -> más potencia entregada.
Se añade un ligero suavizado aleatorio para emular la dispersión del disparo;
``rng`` es el generador de la corrida (``random.Random``). Sin conectar.
"""
from simulador_horno.configuracion import limites


def suavizar_u(u_real: float, rng, intensidad: float = 0.1) -> float:
    u_real = max(0.0, min(1.0, u_real))
    delta = intensidad * u_real
    u_modulado = rng.uniform(u_real - delta, u_real + delta)
    return max(0.0, min(1.0, u_modulado))


def u_a_angulo_conduccion(
    u: float,
    rng,
    theta_min: float = limites.THETA_MIN,
    theta_max: float = limites.THETA_MAX,
    intensidad: float = 0.1,
) -> float:
    u_suavizado = suavizar_u(u, rng, intensidad)
    return theta_max - u_suavizado * (theta_max - theta_min)
