"""Controlador PID.

- ``pid``         : cálculo del PID (``calcular_pid`` puro, ``actualizar_pid`` con estado).
- ``escalado``    : saturación de la señal de control a [-1, 1].
- ``anti_windup`` : recorte del término integral.
"""
