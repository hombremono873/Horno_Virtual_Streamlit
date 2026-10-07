"""El controlador PID (sin entrada/salida).

- ``pid``         : cálculo del PID (``calcular_pid`` puro, ``actualizar_pid`` con estado).
- ``anti_windup`` : recorte del término integral.
- ``escalado``    : saturación de la señal de control a [-1, 1].
- ``senal_error`` : construcción del error de control (setpoint - T + perturbaciones).
"""
