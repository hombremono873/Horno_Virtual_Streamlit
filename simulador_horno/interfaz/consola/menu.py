"""Menú principal del simulador."""
from simulador_horno.interfaz.consola import marco

ITEMS = [
    ("1", "Configurar PID", "Ganancias Kp, Ki, Kd"),
    ("2", "Configurar horno", "T ambiente, setpoint, B, τ, Δt"),
    ("3", "Error oscilante", "Ruido + senoide sobre el error"),
    ("4", "Error de impulso", "Impulsos térmicos probabilísticos"),
    ("5", "Acotar integral", "Límite del término integral [0-1]"),
    ("6", "Ejecutar simulación", "Abre el monitor en tiempo real"),
    ("7", "Salir", "Cerrar el simulador"),
]


def mostrar_menu():
    """Devuelve la clave ('1'..'7') de la opción elegida."""
    return marco.menu_interactivo("MENÚ PRINCIPAL", ITEMS, migas=["Menú"])
