# ================================================================
# CONSTANTES FIJAS DEL SIMULADOR
# ================================================================
# A diferencia de parametros_horno / parametros_pid, estos valores NO
# se editan desde el menú: son límites y ajustes internos del programa.

# --- Controlador -------------------------------------------------
U_MAX = 20000.0        # escala de saturación de la señal de control (control.escalado)
UMBRAL_INTEGRAL = 2000 # tope del anti-windup en modo "recorte" (control.anti_windup)

# --- Velocidad de simulación -------------------------------------
# Relación tiempo simulado / tiempo real. None = "máxima": sin esperas,
# tan rápido como permita el equipo. La aceleración nunca toca DT.
VELOCIDADES = {
    "x1": 1,
    "x10": 10,
    "x60": 60,
    "x600": 600,
    "máxima": None,
}

# --- Duración de la corrida -------------------------------------
# Horas SIMULADAS tras las que la corrida se detiene sola (las gráficas
# quedan a la vista). None = sin límite: corre hasta cerrar el monitor.
DURACIONES_HORAS = (0.5, 1, 2, 4, 8, None)

# --- Simulación ------------------------------------------------
REFRESCO_HZ = 4            # refrescos por segundo real de la tabla rich y las gráficas
INTERVALO_MUESTREO = 1.0   # segundos SIMULADOS entre muestras del historial
HORAS_HISTORIAL = 12       # horas simuladas que conserva el historial (el arranque no se pierde)
MAX_MUESTRAS = int(HORAS_HISTORIAL * 3600 / INTERVALO_MUESTREO)

# --- Archivos de resultados (simulacion.resultados) --------------
# Formato pensado para Excel en español (Colombia): separador ";" y coma
# decimal; con "," y "." Excel abriría todo en una sola columna.
CARPETA_RESULTADOS = "resultados"
CSV_SEPARADOR = ";"
CSV_DECIMAL = ","

# --- Perturbación de impulso (control.senal_error) ----------------
# Tasa expresada por hora SIMULADA para que no dependa de DT. Con ~6/h
# una corrida típica (~75 min) recibe unos 7 impulsos: visibles sin
# saturar la gráfica.
TASA_IMPULSOS_HORA = 6
DURACION_IMPULSO = 3       # s simulados
MAGNITUD_IMPULSO = 80      # °C sumados al error

# --- Perturbaciones sobre la medición y sobre el horno -----------
# (atributo de parametros_horno, nombre visible, sobre qué actúa)
PERTURBACIONES = (
    ("error_oscilante", "Error oscilante", "medición"),
    ("flag_error", "Impulsos en el error", "medición"),
    ("ruido_termopar", "Ruido del termopar", "medición"),
    ("puerta", "Apertura de puerta", "horno"),
    ("red_variable", "Fluctuación de la red", "horno"),
    ("ambiente_variable", "Ambiente variable", "horno"),
)
RUIDO_TERMOPAR_SIGMA = 1.0     # °C: desviación típica del ruido de lectura
# Apertura de la puerta: eventos al azar por hora simulada; mientras está
# abierta las pérdidas se multiplican (pérdida extra = 1/TAU_PUERTA).
TASA_PUERTA_HORA = 2
DURACION_PUERTA = 90           # s simulados
TAU_PUERTA = 1500              # s: con TAU = 3000 las pérdidas se triplican
# Red eléctrica: el voltaje oscila (V/Vn = 1 + suma de senoides) y la
# potencia del calentador es proporcional a V².
RED_AMPLITUDES = (0.04, 0.02)  # fracción del voltaje nominal
RED_PERIODOS = (600, 170)      # s
# Ambiente: T_amb + amplitud·sen(2πt/periodo)
AMBIENTE_AMPLITUD = 10.0       # °C
AMBIENTE_PERIODO = 3600        # s

# --- Escala de color térmico (interfaz.graficas.panel) ---
TEMP_MIN_COLOR = 30
TEMP_MAX_COLOR = 1200

# --- Actuador: ángulo de conducción (modelo.actuador) -------------
THETA_MIN = 10.0
THETA_MAX = 170.0
