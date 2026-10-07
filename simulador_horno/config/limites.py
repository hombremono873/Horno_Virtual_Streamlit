# ================================================================
# CONSTANTES FIJAS DEL SIMULADOR
# ================================================================
# A diferencia de parametros_horno / parametros_pid, estos valores NO
# se editan desde el menú: son límites y ajustes internos del programa.

# --- Controlador -------------------------------------------------
U_MAX = 20000.0        # escala de saturación de la señal de control (pid.escalar_u)
UMBRAL_INTEGRAL = 2000 # a partir de aquí actúa el anti-windup (pid.calcular_pid)

# --- Simulación ------------------------------------------------
MAX_MUESTRAS = 5000    # tamaño máximo de los historiales en memoria
REFRESCO_HZ = 4        # refresco de la tabla rich y de las gráficas

# --- Escala de color térmico (interfaces.graficas.imagen_termica) ---
TEMP_MIN_COLOR = 30
TEMP_MAX_COLOR = 1200

# --- Actuador: ángulo de conducción (control.actuador) -----------
THETA_MIN = 10.0
THETA_MAX = 170.0
