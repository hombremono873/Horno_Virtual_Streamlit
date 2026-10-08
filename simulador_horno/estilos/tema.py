"""Tema visual del simulador.

Un único lugar para la paleta de las gráficas, de modo que todas se vean
como una sola herramienta de instrumentación (la misma identidad que tenía
el monitor de la versión de escritorio).
"""

INSTITUCION = "UNIVERSIDAD DE ANTIOQUIA"
APP_NOMBRE = "SIMULADOR DE HORNO · CONTROL PID"
APP_VERSION = "v3.1"

# ======================================================================
# GRÁFICAS
# ======================================================================
G_FONDO = "#11111b"
G_PANEL = "#181825"
G_TEXTO = "#cdd6f4"
G_CUADRICULA = 0.22        # alpha de la rejilla

G_TEMP = "#a6e3a1"         # curva de temperatura
G_SETPOINT = "#f9e2af"     # línea de referencia
G_ERROR = "#cba6f7"        # curva de error
G_CERO = "#585b70"         # línea de error = 0

MAPA_TERMICO = "plasma"    # escala de color de la franja térmica evolutiva

# Eje Y centrado en el setpoint: el semirango se calcula con la máxima
# desviación de los últimos G_VENTANA_ESCALA_MIN minutos simulados.
G_VENTANA_ESCALA_MIN = 30    # minutos simulados que determinan la escala
G_SEMIRANGO_MIN = 5.0        # °C; la escala nunca se cierra por debajo de ±5 °C
G_HOLGURA_ESCALA = 1.15      # 15 % de aire alrededor de la máxima desviación

# Comparación de métodos numéricos
G_EXACTA = "#f9e2af"       # solución analítica (línea discontinua)
G_METODOS = {
    "euler": "#f38ba8",    # rojo suave
    "heun": "#89b4fa",     # azul
    "rk4": "#a6e3a1",      # verde
}

# Dashboard: un color por corrida comparada (A, B, C...)
G_CORRIDAS = ("#89b4fa", "#f38ba8", "#a6e3a1", "#f9e2af", "#cba6f7", "#fab387", "#94e2d5")
