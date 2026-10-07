# ================================================================
# PARÁMETROS FÍSICOS DEL HORNO
# ================================================================
# Estos valores son una CONFIGURACIÓN POR DEFECTO. El usuario los
# modifica en caliente desde el menú (opción 2 -> formularios.configurar_horno),
# por eso se mantienen como variables de módulo mutables.

T_AMB = 30.0        # Temperatura ambiente (°C)
T_SET = 1000.0      # Setpoint / temperatura objetivo (°C)
B = 100             # Ganancia térmica (°C por unidad de control)
TAU = 3000          # Constante de tiempo del horno (s)
DT = 0.1            # Paso de simulación (s)

# ----------------------------------------------------------------
# Historiales de la corrida en curso (los llena la capa de simulación)
# ----------------------------------------------------------------
tiempos = []
temperaturas = []
errores = []

# ----------------------------------------------------------------
# Estado de las perturbaciones (lo conmutan los formularios del menú)
# ----------------------------------------------------------------
delta_T = 0
flag_error = False        # opción 4: impulso probabilístico
error_oscilante = False   # opción 3: ruido + senoide sobre el error
