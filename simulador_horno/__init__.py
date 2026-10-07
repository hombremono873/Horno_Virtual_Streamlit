"""Simulador de calentamiento de un horno eléctrico con control PID.

Paquete organizado por responsabilidad:

- ``configuracion`` : parámetros editables (horno, PID) y constantes fijas.
- ``modelo``        : lo que se simula — ecuación del horno, perturbaciones, actuador.
- ``control``       : el controlador — PID, anti-windup, saturación y señal de error.
- ``numerico``      : métodos numéricos de integración (Heun, Runge-Kutta 4).
- ``simulacion``    : orquestación del bucle de simulación e historial.
- ``interfaz``      : lo que ve el usuario — consola rich, monitor Qt, alarmas.
- ``estilos``       : paleta y medidas visuales compartidas.
"""
