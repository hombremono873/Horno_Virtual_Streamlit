# ================================================================
# PARÁMETROS DEL CONTROLADOR PID
# ================================================================
# Ganancias con CONFIGURACIÓN POR DEFECTO. El usuario las modifica en
# caliente desde el menú (opción 1 -> formularios.configurar_pid).

KP = 200   # Ganancia proporcional
KI = 10    # Ganancia integral
KD = 2     # Ganancia derivativa

# ----------------------------------------------------------------
# Anti-windup (opción 5 -> formularios.configurar_anti_windup).
#   "ninguno" | "recorte" | "condicional"   (ver control.anti_windup)
# restringir_integral: factor [0, 1] del modo "recorte", que escala la
# integral cuando supera limites.UMBRAL_INTEGRAL.
# ----------------------------------------------------------------
anti_windup = "condicional"
restringir_integral = 0.85

# ----------------------------------------------------------------
# Estado interno del PID entre iteraciones. Lo actualiza
# control.pid.actualizar_pid() en cada paso.
# ----------------------------------------------------------------
error_prev = 0.0
integral = 0.0
derivada = 0.0        # término derivativo ya multiplicado por KD (para la tabla)
proporcional = 0.0    # término proporcional (para la tabla)
