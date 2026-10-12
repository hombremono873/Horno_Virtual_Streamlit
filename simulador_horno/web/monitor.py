"""Monitor del horno como componente de Streamlit que vive en el navegador.

``st.plotly_chart`` reconstruye la gráfica en cada refresco y Streamlit la
atenúa mientras recalcula: en el modo en vivo eso se ve como parpadeo. Este
componente (``st.components.v2``) se monta UNA vez; en cada refresco Python
solo le envía los datos nuevos y el navegador actualiza en su sitio:

- ``lienzo``  : la figura del monitor, con ``Plotly.react`` (cambia los datos
                sin redibujar el lienzo);
- ``tablero`` : las tarjetas de indicadores agrupadas.

Cada uno va en su pestaña. Una pestaña oculta mide 0 px de ancho: al
volver a mostrarse, un ``ResizeObserver`` reajusta la gráfica.

Plotly.js se carga desde un CDN, en la misma versión que usa el paquete
``plotly`` de Python.
"""
import plotly.io as pio
import streamlit as st
from plotly.offline import get_plotlyjs_version

from simulador_horno.estilos import tema

PLOTLY_JS = f"https://cdn.jsdelivr.net/npm/plotly.js-dist-min@{get_plotlyjs_version()}/plotly.min.js"

_CSS = f"""
.horno-monitor {{ color: {tema.G_TEXTO}; font-family: "Source Sans Pro", "Segoe UI", sans-serif; }}
.horno-estado {{ font-size: 0.92rem; min-height: 1.4em; margin: 2px 0 6px; }}
.horno-estado span + span::before {{ content: "  ·  "; opacity: 0.5; white-space: pre; }}
.horno-estado .ok {{ color: {tema.G_TEMP}; }}
.horno-estado .vivo {{ color: {tema.G_CORRIDAS[0]}; }}
.horno-estado .alerta {{ color: {tema.G_SETPOINT}; }}
.horno-tablero {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
.horno-grupo {{ background: {tema.G_PANEL}; border: 1px solid rgba(205,214,244,0.12); border-radius: 10px;
               padding: 12px 16px; }}
.horno-grupo h4 {{ margin: 0 0 8px; font-size: 0.85rem; font-weight: 600; letter-spacing: .04em;
                  text-transform: uppercase; opacity: 0.7; }}
.horno-grupo .ind {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px;
                    padding: 3px 0; border-bottom: 1px solid rgba(205,214,244,0.06); }}
.horno-grupo .e {{ font-size: 0.9rem; opacity: 0.8; }}
.horno-grupo .v {{ font-size: 1.35rem; font-weight: 600; font-variant-numeric: tabular-nums; }}
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

function tablero(grupos) {
    return grupos.map(([nombre, filas]) =>
        `<div class="horno-grupo"><h4>${nombre}</h4>`
        + filas.map(([e, v]) => `<div class="ind"><span class="e">${e}</span><span class="v">${v}</span></div>`).join("")
        + "</div>").join("");
}

export default function (component) {
    const { data, parentElement } = component;
    let raiz = parentElement.querySelector(".horno-monitor");
    if (!raiz) {   // primera vez: se crea la estructura; después solo se actualiza
        raiz = document.createElement("div");
        raiz.className = "horno-monitor";
        raiz.innerHTML = '<div class="horno-estado"></div><div class="horno-tablero"></div>'
                       + '<div class="horno-lienzo"></div>';
        parentElement.appendChild(raiz);
    }
    if (!data) return;
    raiz.querySelector(".horno-estado").innerHTML = (data.estado || []).map((a) => `<span>${a}</span>`).join("");
    const tab = raiz.querySelector(".horno-tablero");
    tab.style.display = data.grupos ? "" : "none";
    if (data.grupos) tab.innerHTML = tablero(data.grupos);

    const lienzo = raiz.querySelector(".horno-lienzo");
    if (!data.figura) { lienzo.style.display = "none"; return; }
    const figura = JSON.parse(data.figura);
    cargarPlotly()
        .then((Plotly) => {
            Plotly.react(lienzo, figura.data, figura.layout, { responsive: true, displaylogo: false });
            if (!lienzo.__observador) {   // al volver a su pestaña (de 0 px al ancho real) se reajusta
                let ancho = lienzo.clientWidth;
                lienzo.__observador = new ResizeObserver(() => {
                    if (lienzo.clientWidth > 0 && lienzo.clientWidth !== ancho) {
                        ancho = lienzo.clientWidth;
                        Plotly.Plots.resize(lienzo);
                    }
                });
                lienzo.__observador.observe(lienzo);
            }
        })
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


def lienzo(figura, estado):
    """Monta (la primera vez) o actualiza el lienzo de las gráficas."""
    datos = {"figura": pio.to_json(figura, validate=False), "estado": list(estado)}
    return _componente()(key="lienzo_horno", data=datos)


def tablero(grupos, estado):
    """Monta o actualiza las tarjetas de indicadores."""
    datos = {"grupos": [[nombre, [list(f) for f in filas]] for nombre, filas in grupos], "estado": list(estado)}
    return _componente()(key="tablero_horno", data=datos)


def grafica(figura, key, estado=()):
    """Cualquier otra figura que se actualiza en vivo sin parpadeo (triac, osciloscopio).

    ``estado``: fragmentos HTML de la línea de texto que va encima de la figura.
    """
    datos = {"figura": pio.to_json(figura, validate=False), "estado": list(estado)}
    return _componente()(key=key, data=datos)
