"""Tema visual del simulador.

Un único lugar para la paleta y las medidas que comparten la interfaz de
consola (rich) y las gráficas (pyqtgraph), de modo que ambas se vean como
una sola herramienta de instrumentación.
"""

# ======================================================================
# CONSOLA (estilos rich)
# ======================================================================
C_MARCO = "grey37"          # borde de paneles secundarios
C_MARCO_ACENTO = "cyan"     # borde del panel activo
C_ACENTO = "cyan"           # color de acento para etiquetas y realces
C_TITULO = "bold cyan"
C_SUBTITULO = "bold white"
C_TEXTO = "white"
C_TENUE = "grey62"          # texto de apoyo, ayudas, unidades
C_OK = "bold green"
C_ALERTA = "bold red"
C_AVISO = "bold yellow"
C_SELECCION = "bold black on cyan"   # fila resaltada en el menú
C_VALOR = "bright_cyan"     # valores numéricos en tablas

INSTITUCION = "UNIVERSIDAD DE ANTIOQUIA"
APP_NOMBRE = "SIMULADOR DE HORNO · CONTROL PID"
APP_VERSION = "v2.0"

# ======================================================================
# GRÁFICAS (pyqtgraph)
# ======================================================================
G_FONDO = "#11111b"
G_PANEL = "#181825"
G_TEXTO = "#cdd6f4"
G_CUADRICULA = 0.22        # alpha de la rejilla

G_TEMP = "#a6e3a1"         # curva de temperatura
G_SETPOINT = "#f9e2af"     # línea de referencia
G_ERROR = "#cba6f7"        # curva de error
G_CERO = "#585b70"         # línea de error = 0

MAPA_TERMICO = "plasma"    # colormap de la franja térmica evolutiva

# Eje Y centrado en el setpoint: el semirango se calcula con la máxima
# desviación de los últimos G_VENTANA_ESCALA_MIN minutos simulados.
G_VENTANA_ESCALA_MIN = 30    # minutos simulados que determinan la escala
G_SEMIRANGO_MIN = 5.0        # °C; la escala nunca se cierra por debajo de ±5 °C
G_HOLGURA_ESCALA = 1.15      # 15 % de aire alrededor de la máxima desviación

VENTANA_TITULO = "Monitor del horno — Simulador PID"
VENTANA_ANCHO = 1280
VENTANA_ALTO = 820
