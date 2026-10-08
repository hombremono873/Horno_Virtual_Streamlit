"""Simulador de calentamiento de un horno eléctrico con control PID.

Paquete organizado por responsabilidad:

- ``configuracion`` : parámetros editables (dataclasses, uno por simulador) y constantes fijas.
- ``modelo``        : lo que se simula — ecuación del horno, perturbaciones, actuador.
- ``control``       : el controlador — PID, anti-windup, saturación y señal de error.
- ``numerico``      : métodos de integración (Euler, Heun, RK4), comparación y estabilidad.
- ``simulacion``    : el ``Simulador`` (una corrida sin E/S), historial, métricas y CSV.
- ``estilos``       : paleta y medidas visuales compartidas.
"""
