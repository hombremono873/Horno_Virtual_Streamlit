"""Capa de orquestación de la simulación.

- ``motor``     : clase ``Motor``, la lógica de cada paso (error -> PID -> planta), sin E/S.
- ``reloj``     : compresión del tiempo de ejecución (pasos por refresco según la velocidad).
- ``historial`` : registro muestreado y recorte de las series temporales de la corrida.
- ``simulador`` : clase ``Simulador``, el bucle visual (motor + tabla en vivo + monitor).
"""
