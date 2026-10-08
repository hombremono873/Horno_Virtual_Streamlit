"""Tabla de desempeño de la corrida (rich).

Presenta un ``simulacion.metricas.Metricas``. Las integrales del error se
muestran en °C·min (y °C²·min): en °C·s los números son de millones y se
leen peor.
"""
from rich import box
from rich.table import Table
from rich.text import Text

from simulador_horno.estilos import tema
from simulador_horno.simulacion.metricas import BANDA_ESTABLECIMIENTO


def _min(segundos):
    return Text("no se alcanzó", style=tema.C_AVISO) if segundos is None else f"{segundos / 60:.1f} min"


def tabla_metricas(m, titulo="Desempeño de la corrida"):
    t = Table(title=titulo, title_style=tema.C_TITULO, box=box.MINIMAL, expand=False)
    t.add_column("Métrica", style=tema.C_TENUE)
    t.add_column("Valor", justify="right", style=tema.C_VALOR)
    if not m.hay_salto:
        t.add_row("Arranque", Text("ya en el setpoint: sin subida que medir", style=tema.C_TENUE))
    else:
        estilo = tema.C_OK if m.sobrepaso_pct < 5 else tema.C_AVISO
        t.add_row("Sobrepaso", Text(f"{m.sobrepaso_pct:.2f} %  ({m.sobrepaso_c:.1f} °C)", style=estilo))
        t.add_row("Tiempo de subida (10→90 %)", _min(m.t_subida))
        t.add_row("Tiempo al 90 %", _min(m.t90))
        t.add_row(f"Establecimiento (±{BANDA_ESTABLECIMIENTO:.0%})", _min(m.t_establecimiento))
    estilo_error = tema.C_OK if abs(m.error_final) < 1 else tema.C_AVISO
    t.add_row("Error final", Text(f"{m.error_final:+.2f} °C", style=estilo_error))
    t.add_row("IAE  ∫|e| dt", f"{m.iae / 60:,.0f} °C·min")
    t.add_row("ISE  ∫e² dt", f"{m.ise / 60:,.0f} °C²·min")
    return t
