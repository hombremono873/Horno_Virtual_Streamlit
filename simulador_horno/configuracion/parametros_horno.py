# ================================================================
# PARÁMETROS FÍSICOS DEL HORNO
# ================================================================
# Estos valores son una CONFIGURACIÓN POR DEFECTO. El usuario los
# modifica en caliente desde el menú (opción 2 -> formularios.configurar_horno),
# por eso se mantienen como variables de módulo mutables.

T_AMB = 30.0        # Temperatura ambiente (°C)
T_SET = 1000.0      # Setpoint / temperatura objetivo (°C)
T_MAX_EQ = 1300.0   # Temperatura de equilibrio a potencia plena, u = 1 (°C)
T_INICIAL = 30.0    # Temperatura del horno al empezar la corrida (°C); = T_AMB es arranque en frío
TAU = 3000          # Constante de tiempo del horno (s)
DT = 0.1            # Paso de integración numérica (s); fijo, NO acelera la simulación


def recalcular_B():
    """Ganancia térmica derivada: con u = 1 el horno se estabiliza en T_MAX_EQ.

    En equilibrio dT/dt = 0  ->  (T_MAX_EQ - T_AMB) / TAU = B
    """
    global B
    tau = TAU if TAU > 0 else 1e-6   # evita división por cero
    B = (T_MAX_EQ - T_AMB) / tau
    return B


B = recalcular_B()  # Ganancia térmica (°C/s por unidad de control); se deriva, no se edita

# ----------------------------------------------------------------
# Historiales de la corrida en curso (los llena la capa de simulación)
# ----------------------------------------------------------------
tiempos = []
temperaturas = []
errores = []
potencias = []      # señal de control u en [0, 1]

# ----------------------------------------------------------------
# Estado de las perturbaciones (lo conmutan los formularios del menú)
# ----------------------------------------------------------------
delta_T = 0
flag_error = False        # opción 4: impulso probabilístico
error_oscilante = False   # opción 3: ruido + senoide sobre el error
