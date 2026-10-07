"""Pantalla de bienvenida."""
from datetime import date

from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from simulador_horno.config import tema
from simulador_horno.interfaces.consola import marco


def mostrar():
    hoy = date.today().strftime("%d/%m/%Y")

    cuerpo = Text(justify="center")
    cuerpo.append(f"{tema.INSTITUCION}\n\n", style=tema.C_SUBTITULO)
    cuerpo.append("SIMULADOR VIRTUAL DE HORNO\nCON CONTROL PID\n\n", style=tema.C_TITULO)
    cuerpo.append(f"Fecha        {hoy}\n", style=tema.C_TENUE)
    cuerpo.append("Asignatura   Métodos Numéricos\n", style=tema.C_TENUE)
    cuerpo.append("Autor        Omar Alberto Torres\n", style=tema.C_TENUE)
    cuerpo.append("Docente      Yony Ceballos\n\n", style=tema.C_TENUE)
    cuerpo.append("Pulsa una tecla para comenzar", style=tema.C_ACENTO)

    panel = Panel(
        Align.center(cuerpo),
        title="Bienvenido",
        subtitle=tema.APP_VERSION,
        box=box.DOUBLE,
        border_style=tema.C_MARCO_ACENTO,
        padding=(2, 6),
    )
    marco.mostrar_info(panel)
