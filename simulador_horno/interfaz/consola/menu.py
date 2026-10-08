"""Menú principal del simulador."""
from simulador_horno.interfaz.consola import marco

ITEMS = [
    ("1", "Configurar PID", "Ganancias Kp, Ki, Kd"),
    ("2", "Configurar horno", "T ambiente, setpoint, T máx., τ, Δt"),
    ("3", "Error oscilante", "Ruido + senoide sobre el error"),
    ("4", "Error de impulso", "Impulsos térmicos probabilísticos"),
    ("5", "Acotar integral", "Límite del término integral [0-1]"),
    ("6", "Velocidad de simulación", "x1, x10, x60, x600 o máxima"),
    ("7", "Método numérico", "Euler, Heun (RK2) o Runge-Kutta 4"),
    ("8", "Ejecutar simulación", "Abre el monitor en tiempo real"),
    ("9", "Salir", "Cerrar el simulador"),
]


def mostrar_menu():
    """Devuelve la clave ('1'..'9') de la opción elegida."""
    return marco.menu_interactivo("MENÚ PRINCIPAL", ITEMS, migas=["Menú"])
