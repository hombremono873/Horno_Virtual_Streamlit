"""Tabla del estudio de estabilidad de los métodos numéricos (rich).

Presenta un ``numerico.estabilidad.ResultadoEstabilidad``: para cada Δt y
cada método, el factor de amplificación R y su veredicto, más el límite
de estabilidad teórico de cada método.
"""
from rich import box
from rich.console import Group
from rich.table import Table
from rich.text import Text

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.estilos import tema
from simulador_horno.numerico.integradores import NOMBRES

_ESTILO_VEREDICTO = {"estable": tema.C_OK, "oscila": tema.C_AVISO, "diverge": tema.C_ALERTA}


def tabla_estabilidad(resultado):
    tau = vhorno.TAU
    t = Table(title="Factor de amplificación R por paso  (estable si |R| < 1)",
              title_style=tema.C_TITULO, box=box.SIMPLE_HEAD, pad_edge=False)
    t.add_column("Δt (s)", justify="right", style=tema.C_TENUE)
    t.add_column("Δt/τ", justify="right", style=tema.C_TENUE)
    for metodo in NOMBRES:
        t.add_column(NOMBRES[metodo], justify="right", style=tema.C_VALOR)
        t.add_column("", justify="left")
    for dt in resultado.dts:
        fila = [f"{dt:g}", f"{dt / tau:g}"]
        for metodo in NOMBRES:
            veredicto = resultado.veredicto(metodo, dt)
            fila.append(f"{resultado.factores[(metodo, dt)]:+.3f}")
            fila.append(Text(veredicto, style=_ESTILO_VEREDICTO[veredicto]))
        t.add_row(*fila)
    t.add_section()
    fila = ["Δt máximo", ""]
    for metodo in NOMBRES:
        limite = resultado.limites[metodo]
        fila += [f"{limite:.0f} s", Text(f"= {limite / tau:.3f}·τ", style=tema.C_TENUE)]
    t.add_row(*fila)
    return t


def resumen_estabilidad(resultado):
    nota = Text(
        f"El horno se enfría desde {resultado.T0:g} °C con la potencia apagada. La física es\n"
        "estable para cualquier Δt: la temperatura siempre baja suavemente hacia T_AMB.\n"
        "Pero cada método multiplica la desviación (T − T_AMB) por R en cada paso:\n"
        "  · 0 < R < 1   se enfría, como la realidad\n"
        "  · −1 < R < 0  cambia de signo en cada paso: oscila alrededor de T_AMB\n"
        "  · |R| > 1     la desviación crece sin límite: temperaturas absurdas\n"
        "Euler y Heun dejan de ser estables con Δt > 2τ; RK4 aguanta hasta ~2,785τ.",
        style=tema.C_TENUE,
    )
    return Group(tabla_estabilidad(resultado), Text(), nota)
