"""Gráficas web con Plotly: el monitor del horno en UN solo lienzo.

Misma disposición e identidad visual que el monitor de escritorio:

    ┌───────────────────────────────┬──────────────┬──┐
    │ Temperatura vs. tiempo        │  PAREDES DEL │°C│
    ├───────────────────────────────┤  HORNO       │  │
    │ Error de control  · u (der.)  │ (colorimetría│  │
    ├───────────────────────────────┴──────────────┤  │
    │ Evolución del color térmico (histórico)      │  │
    └──────────────────────────────────────────────┴──┘

- El eje de temperatura está CENTRADO EN EL SETPOINT y el del error en 0,
  con el mismo semirango: se ve a simple vista cuánto se aleja el horno
  por arriba o por debajo de la referencia. El semirango sale de la
  desviación reciente, así que se abre durante la subida y se cierra al
  estabilizarse.
- El eje de tiempo está en MINUTOS simulados.
- Las series se diezman a ``datos.MAX_PUNTOS`` antes de dibujar.
"""
import math

import plotly.graph_objects as go

from simulador_horno.configuracion import limites
from simulador_horno.estilos import tema
from simulador_horno.modelo.triac import angulo_compensado, fraccion_potencia
from simulador_horno.web.datos import diezmar, indices_diezmados, indices_ventana

ALTO = 640
_CURVAS = (0.0, 0.70)            # columna de las curvas (fracción del ancho)
_HORNO = (0.75, 0.93)            # columna del dibujo del horno
_FILA_T = (0.52, 0.95)
_FILA_E = (0.20, 0.45)
_FILA_FRANJA = (0.0, 0.10)
_ALTO_HORNO, _ANCHO_HORNO, _GROSOR_PARED = 34, 32, 5


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
        font=dict(color=tema.G_TEXTO, family="Inter, Segoe UI, sans-serif", size=12),
        colorway=list(tema.G_CORRIDAS),
        xaxis=eje, yaxis=eje,
        hoverlabel=dict(bgcolor=tema.G_PANEL, font=dict(color=tema.G_TEXTO)),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    ))


PLANTILLA = plantilla()


def semirango(minutos, temperaturas, errores, T_set, ventana_min=tema.G_VENTANA_ESCALA_MIN):
    """Máxima desviación reciente (|T − T_set| o |error|), con holgura y un mínimo.

    ``ventana_min``: minutos finales que se consideran (None = toda la serie).
    Se incluye el error porque con perturbaciones de la medición lleva ruido
    añadido y puede superar la desviación de la temperatura.
    """
    if not minutos:
        return tema.G_SEMIRANGO_MIN
    desde = 0
    if ventana_min is not None:
        limite = minutos[-1] - ventana_min
        while desde < len(minutos) - 1 and minutos[desde] < limite:
            desde += 1
    desviacion = max(max(abs(T - T_set) for T in temperaturas[desde:]),
                     max(abs(e) for e in errores[desde:]))
    return max(desviacion * tema.G_HOLGURA_ESCALA, tema.G_SEMIRANGO_MIN)


def instantanea(historial, etiqueta="Corrida anterior", idx=None):
    """Copia diezmada de una corrida, para superponerla en la siguiente."""
    idx = indices_diezmados(len(historial)) if idx is None else idx
    return {
        "etiqueta": etiqueta,
        "minutos": [t / 60.0 for t in diezmar(historial.tiempos, idx)],
        "temperaturas": diezmar(historial.temperaturas, idx),
        "errores": diezmar(historial.errores, idx),
        "potencias": diezmar(historial.potencias, idx),
    }


def paredes_del_horno(T, T_amb):
    """Imagen del corte del horno: paredes a T y la cavidad algo más fría."""
    cavidad = T_amb + 0.8 * (T - T_amb)
    g = _GROSOR_PARED
    return [[T if (i < g or i >= _ALTO_HORNO - g or j < g or j >= _ANCHO_HORNO - g) else cavidad
             for j in range(_ANCHO_HORNO)] for i in range(_ALTO_HORNO)]


def _titulo(texto, x, y):
    return dict(text=texto, x=x, y=y, xref="paper", yref="paper", xanchor="left", yanchor="bottom",
                showarrow=False, font=dict(size=13, color=tema.G_TEXTO))


def figura_monitor(historial, duracion=None, anterior=None, T_amb=None,
                   ventana_min=tema.G_VENTANA_ESCALA_MIN, muestras_visibles=None, mostrar_entregada=False):
    """Figura del monitor.

    ``duracion`` (s) fija el eje x en [0, duración]; ``anterior`` es una
    ``instantanea`` para superponer; ``ventana_min`` son los minutos que
    determinan la escala centrada (None = toda la corrida).

    ``muestras_visibles`` (modo en vivo): solo se dibujan las últimas N
    muestras y el eje de tiempo abarca N muestras; cuando se llena, la
    gráfica se corre de derecha a izquierda.

    ``mostrar_entregada``: con un triac, dibuja también la potencia que de
    verdad llegó al horno (punteada) junto a la u que pidió el control.
    """
    if muestras_visibles is None:
        idx = indices_diezmados(len(historial))
    else:
        idx = indices_ventana(historial.tiempos, muestras_visibles, historial.intervalo)
    actual = instantanea(historial, "Corrida actual", idx)
    minutos = actual["minutos"]
    hay_datos = bool(minutos)
    T_set = historial.setpoints[-1] if hay_datos else None
    T = historial.temperaturas[-1] if hay_datos else None
    T_amb = (historial.temperaturas[0] if hay_datos else 0.0) if T_amb is None else T_amb

    fig = go.Figure()
    if anterior is not None:
        estilo = dict(color=tema.G_CERO, width=1.6, dash="dot")
        for ejes, clave in (("x/y", "temperaturas"), ("x2/y2", "errores"), ("x2/y3", "potencias")):
            xa, ya = ejes.split("/")
            fig.add_trace(go.Scatter(x=anterior["minutos"], y=anterior[clave], name=anterior["etiqueta"],
                                     line=estilo, legendgroup="anterior", showlegend=clave == "temperaturas",
                                     xaxis=xa, yaxis=ya, hoverinfo="skip"))

    fig.add_trace(go.Scatter(x=minutos, y=diezmar(historial.setpoints, idx), name="Setpoint",
                             line=dict(color=tema.G_SETPOINT, width=1.5, dash="dash"), xaxis="x", yaxis="y"))
    fig.add_trace(go.Scatter(x=minutos, y=actual["temperaturas"], name="Temperatura",
                             line=dict(color=tema.G_TEMP, width=2.2), xaxis="x", yaxis="y"))
    fig.add_trace(go.Scatter(x=minutos, y=actual["errores"], name="Error",
                             line=dict(color=tema.G_ERROR, width=1.8), xaxis="x2", yaxis="y2"))
    fig.add_trace(go.Scatter(x=minutos, y=actual["potencias"], name="u",
                             line=dict(color=tema.G_CORRIDAS[0], width=1.3), opacity=0.8,
                             xaxis="x2", yaxis="y3"))
    if mostrar_entregada:
        fig.add_trace(go.Scatter(x=minutos, y=diezmar(historial.fracciones, idx), name="Potencia entregada",
                                 line=dict(color=tema.G_SETPOINT, width=1.3, dash="dot"),
                                 xaxis="x2", yaxis="y3"))
    fig.add_trace(go.Heatmap(
        x=minutos, y=[0], z=[actual["temperaturas"]], name="Franja térmica",
        colorscale=tema.MAPA_TERMICO.capitalize(), zmin=limites.TEMP_MIN_COLOR, zmax=limites.TEMP_MAX_COLOR,
        colorbar=dict(title=dict(text="°C"), x=0.955, xanchor="left", y=0.5, len=1.0, thickness=14),
        hovertemplate="t = %{x:.1f} min<br>T = %{z:.1f} °C<extra></extra>", xaxis="x3", yaxis="y4",
    ))
    fig.add_trace(go.Heatmap(
        z=paredes_del_horno(T if hay_datos else T_amb, T_amb), name="Paredes del horno",
        colorscale=tema.MAPA_TERMICO.capitalize(), zmin=limites.TEMP_MIN_COLOR, zmax=limites.TEMP_MAX_COLOR,
        showscale=False, hoverinfo="skip", xaxis="x4", yaxis="y5",
    ))

    eje_t = dict(domain=_CURVAS, showticklabels=False)
    fin = None if duracion is None else duracion / 60.0
    if muestras_visibles is not None:
        ancho = muestras_visibles * historial.intervalo / 60.0
        if fin is None or fin > ancho:   # la ventana es más corta que la corrida: se desliza
            ahora = minutos[-1] if hay_datos else 0.0
            eje_t["range"] = [max(0.0, ahora - ancho), max(ancho, ahora)]
            fin = None
    if fin is not None:
        eje_t["range"] = [0, fin]
    fig.update_layout(
        template=PLANTILLA, height=ALTO, hovermode="x unified",
        margin=dict(l=64, r=20, t=34, b=44),
        legend=dict(orientation="h", x=_CURVAS[1], xanchor="right", y=1.0, yanchor="bottom"),
        uirevision="monitor",   # conserva el zoom del usuario entre refrescos
        xaxis=dict(anchor="y", **eje_t),
        yaxis=dict(domain=_FILA_T, title=dict(text="Temperatura (°C)")),
        xaxis2=dict(anchor="y2", matches="x", domain=_CURVAS, showticklabels=False),
        yaxis2=dict(domain=_FILA_E, title=dict(text="Error (°C)"), zeroline=True,
                    zerolinecolor=tema.G_CERO, zerolinewidth=1.5),
        yaxis3=dict(overlaying="y2", side="right", range=[-0.05, 1.05], showgrid=False,
                    tickvals=[0, 0.5, 1], ticksuffix=" u"),
        xaxis3=dict(anchor="y4", matches="x", domain=_CURVAS, title=dict(text="Tiempo simulado (min)")),
        yaxis4=dict(domain=_FILA_FRANJA, showticklabels=False, showgrid=False),
        xaxis4=dict(anchor="y5", domain=_HORNO, visible=False, range=[-0.5, _ANCHO_HORNO - 0.5]),
        yaxis5=dict(domain=(_FILA_E[0], _FILA_T[1]), visible=False, scaleanchor="x4",
                    range=[-0.5, _ALTO_HORNO - 0.5]),
        annotations=[
            _titulo("Temperatura del horno — tendencia", _CURVAS[0], _FILA_T[1] + 0.005),
            _titulo("Error de control (setpoint − medida) · potencia u →", _CURVAS[0], _FILA_E[1] + 0.005),
            _titulo("Evolución del color térmico", _CURVAS[0], _FILA_FRANJA[1] + 0.005),
            _titulo("Paredes del horno", _HORNO[0], _FILA_T[1] + 0.005),
            dict(text=f"<b>{T:.0f} °C</b>" if hay_datos else "", x=sum(_HORNO) / 2,
                 y=(_FILA_E[0] + _FILA_T[1]) / 2, xref="paper", yref="paper", showarrow=False,
                 xanchor="center", yanchor="middle",
                 font=dict(size=24, color="#ffffff"), bgcolor="rgba(0,0,0,0.6)", borderpad=6),
        ],
    )
    if hay_datos:
        s = semirango(minutos, actual["temperaturas"], actual["errores"], T_set, ventana_min)
        fig.update_layout(yaxis_range=[T_set - s, T_set + s], yaxis2_range=[-s, s])
    return fig


def figura_actuador(sim):
    """Curva del triac: fracción de potencia contra ángulo de disparo, con el punto de trabajo.

    - Curva real: 1 − α/180 + sen(2α)/(2π).
    - Recta: lo que supone el ángulo lineal (α = 180·(1 − u)).
    - Punto de trabajo: el ángulo actual y la potencia que de verdad llega;
      con el ángulo lineal se ve además la potencia que pidió el PID.
    """
    act = sim.config.actuador
    angulos = [i * 0.5 for i in range(361)]
    fig = go.Figure()
    for x0, x1 in ((0, act.alfa_min), (act.alfa_max, 180)):
        fig.add_vrect(x0=x0, x1=x1, fillcolor=tema.G_CERO, opacity=0.25, line_width=0)
    fig.add_trace(go.Scatter(x=angulos, y=[1 - a / 180 for a in angulos], name="Supuesto del ángulo lineal",
                             line=dict(color=tema.G_CERO, width=1.5, dash="dash")))
    fig.add_trace(go.Scatter(x=angulos, y=[fraccion_potencia(a) for a in angulos], name="Potencia real del triac",
                             line=dict(color=tema.G_TEMP, width=2.5)))
    u = sim.u
    if act.modo == "ideal":
        alfa, _ = angulo_compensado(u) if 0 < u < 1 else (180.0 if u <= 0 else 0.0, 0)
        puntos = [(alfa, u, "Ángulo que haría falta", tema.G_SETPOINT)]
    else:
        puntos = [(sim.alfa, sim.fraccion, "Potencia entregada", tema.G_SETPOINT)]
        if act.modo == "triac_lineal":
            puntos.append((sim.alfa, u, "Potencia pedida (u)", tema.G_ERROR))
    for alfa, y, nombre, color in puntos:
        if not math.isnan(alfa):
            fig.add_trace(go.Scatter(x=[alfa], y=[y], name=nombre, mode="markers+text",
                                     marker=dict(size=13, color=color, line=dict(color="#000", width=1)),
                                     text=[f"{alfa:.1f}° · {y * 100:.1f} %"],
                                     textposition="top right" if y < 0.85 else "bottom right"))
    fig.add_hline(y=u, line=dict(color=tema.G_ERROR, width=1, dash="dot"))
    fig.update_layout(
        template=PLANTILLA, height=430, margin=dict(l=64, r=20, t=30, b=50),
        xaxis=dict(title=dict(text="Ángulo de disparo α (grados)"), range=[0, 180], dtick=30),
        yaxis=dict(title=dict(text="Fracción de la potencia máxima"), range=[-0.02, 1.05], tickformat=".0%"),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=1, xanchor="right"),
        uirevision="actuador",
    )
    return fig
