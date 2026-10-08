"""Tablas de la comparación de métodos numéricos con la solución exacta (rich).

Presentan un ``numerico.comparacion.ResultadoComparacion``: el error máximo
de cada método para cada Δt con el orden observado, y el costo en
evaluaciones de dT/dt frente a la precisión obtenida.
"""
import math

from rich import box
from rich.console import Group
from rich.table import Table
from rich.text import Text

from simulador_horno.estilos import tema
from simulador_horno.numerico.integradores import NOMBRES, ORDEN


def _orden_texto(orden, teorico):
    if math.isnan(orden):
        return Text("—", style=tema.C_TENUE)
    estilo = tema.C_OK if abs(orden - teorico) < 0.15 else tema.C_AVISO
    return Text(f"{orden:.2f}", style=estilo)


def tabla_errores(resultado):
    """Error máximo |T_num − T_exacta| por Δt y método, con el orden observado."""
    t = Table(title="Error máximo frente a la solución exacta (°C)", title_style=tema.C_TITULO,
              box=box.SIMPLE_HEAD, pad_edge=False)
    t.add_column("Δt (s)", justify="right", style=tema.C_TENUE)
    for metodo in NOMBRES:
        t.add_column(NOMBRES[metodo], justify="right", style=tema.C_VALOR)
        t.add_column("orden", justify="right")
    for i, dt in enumerate(resultado.dts):
        fila = [f"{dt:g}"]
        for metodo in NOMBRES:
            fila.append(f"{resultado.error(metodo, dt):.2e}")
            # el orden se estima entre este Δt y el anterior (el doble)
            fila.append(_orden_texto(resultado.ordenes[metodo][i - 1], ORDEN[metodo])
                        if i else Text("", style=tema.C_TENUE))
        t.add_row(*fila)
    resumen = ["orden medio"]
    for metodo in NOMBRES:
        media = sum(resultado.ordenes[metodo]) / len(resultado.ordenes[metodo])
        resumen += [Text(f"teórico {ORDEN[metodo]}", style=tema.C_TENUE), _orden_texto(media, ORDEN[metodo])]
    t.add_section()
    t.add_row(*resumen)
    return t


def tabla_costo(resultado):
    """Costo (evaluaciones de dT/dt) frente a precisión para cada combinación."""
    t = Table(title="Costo vs. precisión", title_style=tema.C_TITULO,
              box=box.SIMPLE_HEAD, pad_edge=False)
    t.add_column("Método", style=tema.C_TENUE)
    t.add_column("Δt (s)", justify="right")
    t.add_column("Evaluaciones de dT/dt", justify="right", style=tema.C_VALOR)
    t.add_column("Error máximo (°C)", justify="right", style=tema.C_VALOR)
    for metodo in NOMBRES:
        for dt in (max(resultado.dts), min(resultado.dts)):
            tray = resultado.trayectorias[(metodo, dt)]
            t.add_row(NOMBRES[metodo], f"{dt:g}", f"{tray.evaluaciones}", f"{tray.error_maximo:.2e}")
    return t


def resumen_comparacion(resultado):
    nota = Text(
        "Al dividir Δt a la mitad, el error de un método de orden p se divide por ~2^p:\n"
        "Euler (p = 1) lo reduce a la mitad, Heun (p = 2) a la cuarta parte y RK4 (p = 4)\n"
        "a la dieciseisava parte. Con pocas evaluaciones, un método de orden alto es\n"
        "mucho más preciso que uno de orden bajo con muchas.",
        style=tema.C_TENUE,
    )
    return Group(tabla_errores(resultado), Text(), tabla_costo(resultado), Text(), nota)
