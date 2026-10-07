"""Formularios de configuración: PID, horno, perturbaciones y límite integral.

Cada formulario escribe directamente sobre los módulos de ``configuracion`` para que
el cambio surta efecto en la siguiente simulación. ENTER conserva el valor
actual en cada campo.
"""
from rich.text import Text

from simulador_horno.configuracion import parametros_horno as horno
from simulador_horno.configuracion import parametros_pid as pid
from simulador_horno.interfaz.consola import marco

console = marco.console


# ----------------------------------------------------------------------
# PID (opción 1)
# ----------------------------------------------------------------------
_AYUDA_PID = Text.from_markup(
    "Ganancias del controlador. ENTER conserva el valor actual.\n\n"
    "[b]Kp[/b]  proporcional · responde al error instantáneo\n"
    "[b]Ki[/b]  integral · corrige el error acumulado\n"
    "[b]Kd[/b]  derivativa · amortigua y anticipa"
)


def configurar_pid():
    marco.cabecera_seccion("CONFIGURAR CONTROLADOR PID", _AYUDA_PID, migas=["Configurar PID"])
    pid.KP = marco.pedir_float("Kp", pid.KP)
    pid.KI = marco.pedir_float("Ki", pid.KI)
    pid.KD = marco.pedir_float("Kd", pid.KD)
    marco.resumen("PID actualizado", {"Kp": f"{pid.KP:g}", "Ki": f"{pid.KI:g}", "Kd": f"{pid.KD:g}"})


# ----------------------------------------------------------------------
# Horno (opción 2)
# ----------------------------------------------------------------------
_AYUDA_HORNO = Text.from_markup(
    "Parámetros físicos del horno. ENTER conserva el valor actual.\n\n"
    "[b]T_AMB[/b]  temperatura ambiente (°C)\n"
    "[b]T_SET[/b]  temperatura objetivo (°C)\n"
    "[b]B[/b]      ganancia térmica (°C por unidad de control)\n"
    "[b]TAU[/b]    constante de tiempo (s)\n"
    "[b]DT[/b]     paso de simulación (s)"
)


def configurar_horno():
    marco.cabecera_seccion("CONFIGURAR HORNO", _AYUDA_HORNO, migas=["Configurar horno"])
    horno.T_AMB = marco.pedir_float("T ambiente (T_AMB)", horno.T_AMB)
    horno.T_SET = marco.pedir_float("Setpoint (T_SET)", horno.T_SET)
    horno.B = marco.pedir_float("Ganancia térmica (B)", horno.B)
    horno.TAU = marco.pedir_float("Constante de tiempo (TAU)", horno.TAU)
    horno.DT = marco.pedir_float("Paso de tiempo (DT)", horno.DT)
    marco.resumen("Horno actualizado", {
        "T_AMB": f"{horno.T_AMB:g} °C",
        "T_SET": f"{horno.T_SET:g} °C",
        "B": f"{horno.B:g}",
        "TAU": f"{horno.TAU:g} s",
        "DT": f"{horno.DT:g} s",
    })


# ----------------------------------------------------------------------
# Perturbaciones (opciones 3 y 4)
# ----------------------------------------------------------------------
def _conmutar(titulo, descripcion, atributo, migas):
    actual = getattr(horno, atributo)
    estado = "[bold green]ACTIVADA[/]" if actual else "[dim]desactivada[/]"
    ayuda = Text.from_markup(f"{descripcion}\n\nEstado actual: {estado}")
    marco.cabecera_seccion(titulo, ayuda, migas=migas)
    nuevo = marco.confirmar("¿Activar esta perturbación?", actual)
    setattr(horno, atributo, nuevo)
    marco.resumen(titulo, {"estado": "activada" if nuevo else "desactivada"})


def configurar_error_oscilante():
    _conmutar(
        "ERROR OSCILANTE",
        "Suma al error una componente senoidal suave más ruido aleatorio.",
        "error_oscilante",
        ["Error oscilante"],
    )


def configurar_error_impulso():
    _conmutar(
        "ERROR DE IMPULSO",
        "Inyecta impulsos térmicos probabilísticos de signo alternante.",
        "flag_error",
        ["Error de impulso"],
    )


# ----------------------------------------------------------------------
# Límite de la integral (opción 5)
# ----------------------------------------------------------------------
_AYUDA_INTEGRAL = Text.from_markup(
    "Factor [0-1] que recorta el término integral cuando supera el umbral,\n"
    "para reducir el efecto 'windup'.\n\n"
    "1 = sin recorte · valores menores recortan más agresivamente."
)


def acotar_integral():
    marco.cabecera_seccion("ACOTAR TÉRMINO INTEGRAL", _AYUDA_INTEGRAL, migas=["Acotar integral"])
    while True:
        valor = marco.pedir_float("Límite de la integral [0-1]", pid.restringir_integral)
        if 0.0 <= valor <= 1.0:
            pid.restringir_integral = valor
            break
        console.print("[bold red]  El valor debe estar entre 0 y 1.[/]")
    marco.resumen("Límite integral actualizado", {"restringir_integral": f"{pid.restringir_integral:g}"})
