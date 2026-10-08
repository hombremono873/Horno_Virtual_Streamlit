"""Monitor del horno como componente de Streamlit que vive en el navegador.

``st.plotly_chart`` reconstruye la gráfica en cada refresco y Streamlit la
atenúa mientras recalcula: en el modo en vivo eso se ve como parpadeo. Este
componente (``st.components.v2``) se monta UNA vez; en cada refresco Python
solo le envía la figura nueva y el navegador la actualiza en su sitio con
``Plotly.react``, que cambia los datos sin redibujar el lienzo.

Plotly.js se carga desde un CDN, en la misma versión que usa el paquete
``plotly`` de Python.
"""
import json

import plotly.io as pio
import streamlit as st
from plotly.offline import get_plotlyjs_version

from simulador_horno.estilos import tema

PLOTLY_JS = f"https://cdn.jsdelivr.net/npm/plotly.js-dist-min@{get_plotlyjs_version()}/plotly.min.js"

_CSS = f"""
.horno-monitor {{ color: {tema.G_TEXTO}; font-family: "Source Sans Pro", "Segoe UI", sans-serif; }}
.horno-indicadores {{ display: flex; flex-wrap: wrap; gap: 6px 22px; margin: 2px 0 6px; }}
.horno-indicadores .ind {{ display: flex; flex-direction: column; min-width: 92px; }}
.horno-indicadores .e {{ font-size: 0.78rem; opacity: 0.75; }}
.horno-indicadores .v {{ font-size: 1.45rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
.horno-estado {{ font-size: 0.92rem; min-height: 1.4em; margin-bottom: 2px; }}
.horno-estado span + span::before {{ content: "  ·  "; opacity: 0.5; white-space: pre; }}
.horno-estado .ok {{ color: {tema.G_TEMP}; }}
.horno-estado .vivo {{ color: {tema.G_CORRIDAS[0]}; }}
.horno-estado .alerta {{ color: {tema.G_SETPOINT}; }}
.horno-lienzo {{ width: 100%; }}
"""

_JS = """
const CDN = "%s";

function cargarPlotly() {
    if (window.Plotly) return Promise.resolve(window.Plotly);
    if (!window.__hornoPlotly) {
        window.__hornoPlotly = new Promise((resolver, fallar) => {
            const s = document.createElement("script");
            s.src = CDN;
            s.onload = () => resolver(window.Plotly);
            s.onerror = () => { window.__hornoPlotly = null; fallar(new Error("No se pudo cargar Plotly.js (¿hay conexión a internet?)")); };
            document.head.appendChild(s);
        });
    }
    return window.__hornoPlotly;
}

export default function (component) {
    const { data, parentElement } = component;
    let raiz = parentElement.querySelector(".horno-monitor");
    if (!raiz) {   // primera vez: se crea el lienzo; después solo se actualiza
        raiz = document.createElement("div");
        raiz.className = "horno-monitor";
        raiz.innerHTML = '<div class="horno-indicadores"></div><div class="horno-estado"></div>'
                       + '<div class="horno-lienzo"></div>';
        parentElement.appendChild(raiz);
    }
    if (!data) return;
    raiz.querySelector(".horno-indicadores").innerHTML = data.indicadores
        .map(([e, v]) => `<div class="ind"><span class="e">${e}</span><span class="v">${v}</span></div>`)
        .join("");
    raiz.querySelector(".horno-estado").innerHTML = data.estado.map((a) => `<span>${a}</span>`).join("");
    const lienzo = raiz.querySelector(".horno-lienzo");
    const figura = JSON.parse(data.figura);
    cargarPlotly()
        .then((Plotly) => Plotly.react(lienzo, figura.data, figura.layout,
                                       { responsive: true, displaylogo: false }))
        .catch((error) => { lienzo.textContent = error.message; });
}
""" % PLOTLY_JS

_registro = {"gestor": None, "componente": None}


def _componente():
    """El componente registrado en el runtime actual de Streamlit.

    Se registra una vez por runtime (el servidor tiene uno; las pruebas con
    AppTest crean uno nuevo por sesión simulada).
    """
    gestor = st.components.v2.get_bidi_component_manager()
    if _registro["gestor"] is not gestor:
        _registro["componente"] = st.components.v2.component(
            "monitor_horno", css=_CSS, js=_JS, isolate_styles=False)
        _registro["gestor"] = gestor
    return _registro["componente"]

# Streamlit atenúa los elementos mientras una ejecución está en curso; en
# el modo en vivo (4 ejecuciones por segundo) eso es parpadeo.
ESTILOS_GLOBALES = """
<style>
[data-stale="true"], .stale-element { opacity: 1 !important; transition: none !important; }
.block-container { padding-top: 3.2rem; padding-bottom: 1rem; }
</style>
"""


def mostrar(figura, indicadores, estado):
    """Monta (la primera vez) o actualiza el monitor."""
    datos = {
        "figura": pio.to_json(figura, validate=False),
        "indicadores": [list(par) for par in indicadores],
        "estado": list(estado),
    }
    json.dumps(datos)   # falla aquí, con un error claro, si algo no es serializable
    return _componente()(key="monitor_horno", data=datos)
