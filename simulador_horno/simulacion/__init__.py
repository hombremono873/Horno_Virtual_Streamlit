"""Capa de orquestación de la simulación (sin E/S de interfaz).

- ``simulador``  : clase ``Simulador``, una corrida completa (configuración, PID,
                   perturbaciones e historial) y la lógica de cada paso.
- ``reloj``      : compresión del tiempo de ejecución (pasos por refresco según la velocidad).
- ``historial``  : registro muestreado y recorte de las series temporales de la corrida.
- ``metricas``   : sobrepaso, tiempos de subida y establecimiento, IAE e ISE.
- ``resultados`` : guardado y lectura de corridas en CSV.
"""
