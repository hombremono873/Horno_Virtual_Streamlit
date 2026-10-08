"""Marco visual común de la interfaz de consola.

Todas las pantallas comparten el mismo esquema:

    ┌─ encabezado (institución · aplicación · versión) ─┐
    │              migas de navegación                  │
    │                                                   │
    │              cuerpo centrado                       │
    │                                                   │
    └─ pie (atajos de teclado) ─────────────────────────┘

La navegación es por teclado directo (``readchar``): flechas + Enter, o la
tecla del número.
"""
import readchar
from readchar import key as K
from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.columns import Columns
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.configuracion import parametros_simulacion as vsim
from simulador_horno.control.anti_windup import NOMBRES as NOMBRES_ANTI_WINDUP
from simulador_horno.estilos import tema
from simulador_horno.numerico.integradores import NOMBRES as NOMBRES_METODOS

console = Console()

ATAJOS_MENU = [("↑ ↓", "moverse"), ("1-9", "acceso directo"), ("Enter", "elegir"), ("Q · Esc", "salir")]
ATAJOS_INFO = [("cualquier tecla", "continuar")]


def texto_duracion(horas):
    """``0.5`` -> ``'30 min'``, ``2`` -> ``'2 h'``, ``None`` -> ``'sin límite'``."""
    if horas is None:
        return "sin límite"
    return f"{horas * 60:g} min" if horas < 1 else f"{horas:g} h"


# ======================================================================
# Lectura de teclado
# ======================================================================
def leer_tecla():
    """Devuelve la tecla pulsada. Ctrl+C se traduce en KeyboardInterrupt."""
    k = readchar.readkey()
    if k == K.CTRL_C:
        raise KeyboardInterrupt
    return k


def pausa(mensaje="Pulsa una tecla para volver al menú"):
    console.print()
    console.print(Align.center(Text(f"  {mensaje}  ", style=f"{tema.C_TENUE} reverse")))
    leer_tecla()


# ======================================================================
# Piezas del marco
# ======================================================================
def _encabezado(migas):
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="center")
    grid.add_column(justify="right")
    grid.add_row(
        Text(f" {tema.INSTITUCION}", style=tema.C_SUBTITULO),
        Text(tema.APP_NOMBRE, style=tema.C_TITULO),
        Text(f"{tema.APP_VERSION} ", style=tema.C_TENUE),
    )
    ruta = "  ›  ".join(["Inicio", *migas]) if migas else "Inicio"
    return Group(
        Panel(grid, box=box.HEAVY, border_style=tema.C_MARCO, padding=(0, 1)),
        Text(f" {ruta}", style=tema.C_TENUE),
    )


def _pie(atajos):
    txt = Text()
    for i, (tecla, desc) in enumerate(atajos):
        if i:
            txt.append("      ", style=tema.C_TENUE)
        txt.append(f" {tecla} ", style=f"reverse {tema.C_ACENTO}")
        txt.append(f" {desc}", style=tema.C_TENUE)
    return Panel(Align.center(txt), box=box.HEAVY, border_style=tema.C_MARCO, padding=(0, 1))


def _lienzo(cuerpo, migas, atajos):
    layout = Layout()
    layout.split_column(
        Layout(_encabezado(migas), name="encabezado", size=4),
        Layout(Align.center(cuerpo, vertical="middle"), name="cuerpo"),
        Layout(_pie(atajos), name="pie", size=3),
    )
    return layout


def panel_estado():
    """Resumen en vivo de la configuración de control y planta."""
    t = Table.grid(padding=(0, 2))
    t.add_column(justify="right", style=tema.C_TENUE)
    t.add_column(justify="left", style=tema.C_VALOR)
    t.add_row("Kp", f"{vpid.KP:g}")
    t.add_row("Ki", f"{vpid.KI:g}")
    t.add_row("Kd", f"{vpid.KD:g}")
    t.add_row("Anti-windup", NOMBRES_ANTI_WINDUP[vpid.anti_windup] + (f" ({vpid.restringir_integral:g})" if vpid.anti_windup == "recorte" else ""))
    t.add_row("", "")
    t.add_row("T. objetivo", f"{vhorno.T_SET:g} °C")
    t.add_row("T. ambiente", f"{vhorno.T_AMB:g} °C")
    t.add_row("T. máx. equilibrio", f"{vhorno.T_MAX_EQ:g} °C")
    t.add_row("Ganancia B", f"{vhorno.B:.4f} °C/s")
    t.add_row("Constante τ", f"{vhorno.TAU:g} s")
    t.add_row("Paso Δt", f"{vhorno.DT:g} s")
    activas = [n for n, on in (("oscilante", vhorno.error_oscilante), ("impulso", vhorno.flag_error)) if on]
    t.add_row("Perturbación", ", ".join(activas) or "ninguna")
    t.add_row("Velocidad", vsim.velocidad)
    t.add_row("Duración", texto_duracion(vsim.duracion_horas))
    t.add_row("Método numérico", NOMBRES_METODOS.get(vsim.metodo, vsim.metodo))
    return Panel(
        t, title="Estado del sistema", title_align="left",
        box=box.ROUNDED, border_style=tema.C_MARCO, padding=(1, 2),
    )


# ======================================================================
# Pantallas
# ======================================================================
def mostrar_info(cuerpo, *, migas=None, esperar=True):
    """Muestra una pantalla estática y (opcional) espera una tecla."""
    with console.screen():
        console.print(_lienzo(cuerpo, migas or [], ATAJOS_INFO), height=console.height)
        if esperar:
            leer_tecla()


def menu_interactivo(titulo, items, *, migas=None, inicial=0):
    """Menú navegable. ``items`` = lista de ``(clave, etiqueta, descripción)``.

    Devuelve la ``clave`` elegida. Esc o 'q' devuelven la clave del último ítem.
    ``inicial`` es el índice resaltado al abrir.
    """
    claves = [c for c, _, _ in items]
    idx = inicial
    with console.screen() as pantalla:
        while True:
            filas = Table.grid(padding=(0, 1))
            filas.add_column(width=3)
            filas.add_column(width=4, justify="center")
            filas.add_column()
            for i, (clave, etiqueta, desc) in enumerate(items):
                activo = i == idx
                filas.add_row(
                    Text("▶" if activo else " ", style=tema.C_ACENTO),
                    Text(clave, style=tema.C_SELECCION if activo else tema.C_TENUE),
                    Text(
                        f"{etiqueta}\n  {desc}" if activo else etiqueta,
                        style=tema.C_SELECCION if activo else tema.C_TEXTO,
                    ),
                )
            panel_menu = Panel(
                filas, title=titulo, title_align="left",
                box=box.ROUNDED, border_style=tema.C_MARCO_ACENTO, padding=(1, 2),
            )
            cuerpo = Columns([panel_menu, panel_estado()], padding=(0, 3), expand=False)
            pantalla.update(_lienzo(cuerpo, migas or [], ATAJOS_MENU))

            k = leer_tecla()
            if k == K.UP:
                idx = (idx - 1) % len(items)
            elif k == K.DOWN:
                idx = (idx + 1) % len(items)
            elif k in (K.ENTER, "\r", "\n"):
                return claves[idx]
            elif k in claves:
                return k
            elif k in (K.ESC, "q", "Q"):
                return claves[-1]


# ======================================================================
# Ayudas para los formularios
# ======================================================================
def cabecera_seccion(titulo, ayuda, *, migas=None):
    """Encabezado + panel de ayuda para una pantalla de formulario."""
    console.clear()
    console.print(_encabezado(migas or []))
    console.print()
    console.print(
        Panel(ayuda, title=titulo, title_align="left",
              box=box.ROUNDED, border_style=tema.C_MARCO_ACENTO, padding=(1, 2))
    )
    console.print()


def pedir_float(nombre, actual):
    """Pide un número reutilizando el valor actual como propuesta (ENTER lo conserva)."""
    while True:
        texto = Prompt.ask(f"[{tema.C_ACENTO}]{nombre}[/]", default=f"{actual:g}", console=console)
        try:
            return float(texto)
        except ValueError:
            console.print(f"[{tema.C_ALERTA}]  Solo se permiten números reales.[/]")


def confirmar(pregunta, actual):
    """Pregunta sí/no reutilizando el estado actual como propuesta."""
    return Confirm.ask(f"[{tema.C_ACENTO}]{pregunta}[/]", default=bool(actual), console=console)


def resumen(titulo, filas, *, ok=True):
    t = Table.grid(padding=(0, 2))
    t.add_column(justify="right", style=tema.C_TENUE)
    t.add_column(style=tema.C_VALOR)
    for k, v in filas.items():
        t.add_row(k, str(v))
    console.print()
    console.print(
        Panel(t, title=("✓ " if ok else "✗ ") + titulo, title_align="left",
              box=box.ROUNDED, border_style=(tema.C_OK if ok else tema.C_ALERTA), padding=(1, 2))
    )
