# ================================================================
# PARÁMETROS DEL CONTROLADOR PID
# ================================================================
# Ganancias con CONFIGURACIÓN POR DEFECTO. El usuario las modifica en
# caliente desde el menú (opción 1 -> formularios.configurar_pid).

KP = 35    # Ganancia proporcional
KI = 10    # Ganancia integral
KD = 2     # Ganancia derivativa

# ----------------------------------------------------------------
# Límite del efecto integral (opción 5 -> formularios.acotar_integral).
# Valor en [0, 1] que escala la integral cuando supera el umbral.
# ----------------------------------------------------------------
restringir_integral = 0.85

# ----------------------------------------------------------------
# Estado interno del PID entre iteraciones. Lo actualiza
# control.pid.actualizar_pid() en cada paso.
# ----------------------------------------------------------------
error_prev = 0.0
integral = 0.0
derivada = 0.0        # término derivativo ya multiplicado por KD (para la tabla)
proporcional = 0.0    # término proporcional (para la tabla)
