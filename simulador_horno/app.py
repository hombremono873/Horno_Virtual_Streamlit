"""Aplicación: pantalla de bienvenida y bucle del menú principal.

El menú despacha por tabla (``ACCIONES``) en lugar de una cadena de if/elif.
La navegación es por teclado directo (ver ``interfaz.consola.marco``).
"""
from simulador_horno.estilos import tema
from simulador_horno.interfaz.consola import bienvenida, formularios, marco, menu
from simulador_horno.simulacion.simulador import Simulador


def _correr_simulacion():
    Simulador().ejecutar()


ACCIONES = {
    "1": formularios.configurar_pid,
    "2": formularios.configurar_horno,
    "3": formularios.configurar_perturbaciones,
    "4": formularios.comparar_corridas,
    "5": formularios.configurar_anti_windup,
    "6": formularios.configurar_velocidad,
    "7": formularios.configurar_metodo,
    "8": _correr_simulacion,
}

OPCION_SIMULAR = "8"   # vuelve al menú sin pausa (la simulación ya la pidió)
OPCION_SALIR = "9"


def ejecutar():
    try:
        bienvenida.mostrar()
        while True:
            opcion = menu.mostrar_menu()
            if opcion == OPCION_SALIR:
                break
            accion = ACCIONES.get(opcion)
            if accion is None:
                continue
            accion()
            if opcion != OPCION_SIMULAR:
                marco.pausa()
        marco.console.clear()
        marco.console.print(f"[{tema.C_ALERTA}]Simulador cerrado.[/]")
    except KeyboardInterrupt:
        marco.console.clear()
        marco.console.print(f"\n[{tema.C_ALERTA}]Interrumpido. Simulador cerrado.[/]")
