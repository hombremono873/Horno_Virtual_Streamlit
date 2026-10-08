"""Gráficas web con Plotly: la misma identidad visual del monitor de escritorio.

Una figura con cuatro subgráficas que comparten el eje de tiempo (minutos
simulados):

    Temperatura (con el setpoint) · Error (con la línea en cero)
    Señal de control u (0 a 1)    · Franja térmica (Heatmap "Plasma")

Las series se diezman a ``datos.MAX_PUNTOS`` antes de dibujar.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from simulador_horno.configuracion import limites
from simulador_horno.estilos import tema
from simulador_horno.web.datos import diezmar, indices_diezmados

ALTO = 760
_FILAS = ("Temperatura (°C)", "Error de control (°C)", "Señal de control u", "Franja térmica")


def _rgba(color_hex, alpha):
    r, g, b = (int(color_hex[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def plantilla():
    """Plantilla de Plotly construida con los colores de ``estilos.tema``."""
    rejilla = _rgba(tema.G_TEXTO, tema.G_CUADRICULA)
    eje = dict(gridcolor=rejilla, zerolinecolor=rejilla, linecolor=rejilla, showline=True)
    return go.layout.Template(layout=go.Layout(
        paper_bgcolor=tema.G_FONDO,
        plot_bgcolor=tema.G_PANEL,
        font=dict(color=tema.G_TEXTO, family="Inter, Segoe UI, sans-serif", size=13),
        colorway=list(tema.G_CORRIDAS),
        xaxis=eje, yaxis=eje,
        hoverlabel=dict(bgcolor=tema.G_PANEL, font=dict(color=tema.G_TEXTO)),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    ))


PLANTILLA = plantilla()


def instantanea(historial, etiqueta="Corrida anterior"):
    """Copia diezmada de una corrida, para superponerla en la siguiente."""
    idx = indices_diezmados(len(historial))
    return {
        "etiqueta": etiqueta,
        "minutos": [t / 60.0 for t in diezmar(historial.tiempos, idx)],
        "temperaturas": diezmar(historial.temperaturas, idx),
        "errores": diezmar(historial.errores, idx),
        "potencias": diezmar(historial.potencias, idx),
    }


def figura_monitor(historial, duracion=None, anterior=None):
    """Figura del monitor. ``duracion`` (s) fija el eje x en [0, duración]."""
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.045,
                        row_heights=(0.40, 0.22, 0.22, 0.16), subplot_titles=_FILAS)
    actual = instantanea(historial, "Corrida actual")
    idx = indices_diezmados(len(historial))
    minutos = actual["minutos"]

    if anterior is not None:
        estilo = dict(color=tema.G_CERO, width=1.6, dash="dot")
        for fila, clave in ((1, "temperaturas"), (2, "errores"), (3, "potencias")):
            fig.add_trace(go.Scatter(x=anterior["minutos"], y=anterior[clave], name=anterior["etiqueta"],
                                     line=estilo, legendgroup="anterior", showlegend=fila == 1),
                          row=fila, col=1)

    fig.add_trace(go.Scatter(x=minutos, y=diezmar(historial.setpoints, idx), name="Setpoint",
                             line=dict(color=tema.G_SETPOINT, width=1.5, dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=minutos, y=actual["temperaturas"], name="Temperatura",
                             line=dict(color=tema.G_TEMP, width=2.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=minutos, y=actual["errores"], name="Error",
                             line=dict(color=tema.G_ERROR, width=1.8)), row=2, col=1)
    fig.add_hline(y=0, line=dict(color=tema.G_CERO, width=1), row=2, col=1)
    fig.add_trace(go.Scatter(x=minutos, y=actual["potencias"], name="u",
                             line=dict(color=tema.G_CORRIDAS[0], width=1.8)), row=3, col=1)
    fig.add_trace(go.Heatmap(
        x=minutos, y=[0], z=[actual["temperaturas"]], name="Franja térmica",
        colorscale=tema.MAPA_TERMICO.capitalize(),
        zmin=limites.TEMP_MIN_COLOR, zmax=limites.TEMP_MAX_COLOR,
        colorbar=dict(title=dict(text="°C"), len=0.45, y=0.0, yanchor="bottom", thickness=14),
        hovertemplate="t = %{x:.1f} min<br>T = %{z:.1f} °C<extra></extra>",
    ), row=4, col=1)

    fig.update_yaxes(range=[-0.05, 1.05], row=3, col=1)
    fig.update_yaxes(showticklabels=False, showgrid=False, row=4, col=1)
    fig.update_xaxes(title_text="Tiempo simulado (min)", row=4, col=1)
    if duracion is not None:
        fig.update_xaxes(range=[0, duracion / 60.0])
    fig.update_layout(
        template=PLANTILLA, height=ALTO, hovermode="x unified",
        margin=dict(l=60, r=30, t=40, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
        uirevision="monitor",   # conserva el zoom del usuario entre refrescos
    )
    return fig
