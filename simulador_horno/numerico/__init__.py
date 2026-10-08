"""Métodos numéricos de integración del modelo térmico.

- ``integradores`` : Euler, Heun (RK2) y Runge-Kutta 4 sobre la ecuación del horno,
                     y la tabla ``METODOS`` con la que se elige uno.
- ``comparacion``  : error frente a la solución exacta y orden de convergencia observado.
- ``estabilidad``  : factor de amplificación R(z) y límites de Δt estable.
"""
