"""Pantalla de bienvenida con los créditos del proyecto.

Animada solo con CSS (sin JavaScript): el horno se calienta del morado al
amarillo con la escala Plasma mientras un contador sube de 30 a 1000 °C,
la curva de calentamiento se dibuja hasta el setpoint y los créditos
aparecen uno a uno. Debajo, el botón para abrir el simulador.
"""
import math
from html import escape

import streamlit as st

from simulador_horno import creditos
from simulador_horno.estilos import tema

_PLASMA = ("#0d0887", "#6a00a8", "#b12a90", "#e16462", "#fca636", "#f0f921")
_DURACION = 4.5   # s de la animación de calentamiento


def _curva(ancho=520, alto=150, n=60):
    """Trazo SVG de una subida de primer orden con un pequeño sobrepaso."""
    puntos = []
    for i in range(n + 1):
        x = i / n
        y = 1 - math.exp(-4.2 * x) + 0.035 * math.exp(-6 * (x - 0.62) ** 2 / 0.02)
        puntos.append(f"{x * ancho:.1f},{alto - y * (alto - 18) - 6:.1f}")
    return "M" + " L".join(puntos)


_OCULTAR_BARRA = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
</style>
"""


def _css():
    paradas = "".join(f"{i * 100 // (len(_PLASMA) - 1)}% {{ --c: {c}; }}" for i, c in enumerate(_PLASMA))
    return f"""
@property --temp {{ syntax: '<integer>'; initial-value: 30; inherits: false; }}
@property --c {{ syntax: '<color>'; initial-value: {_PLASMA[0]}; inherits: true; }}
@keyframes calentar {{ from {{ --temp: 30; }} to {{ --temp: 1000; }} }}
@keyframes color {{ {paradas} }}
@keyframes trazo {{ to {{ stroke-dashoffset: 0; }} }}
@keyframes aparecer {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes latido {{ 50% {{ filter: drop-shadow(0 0 26px var(--c)); }} }}
.hv-portada {{ max-width: 980px; margin: 0 auto; color: {tema.G_TEXTO}; text-align: center;
              font-family: "Source Sans Pro", "Segoe UI", sans-serif; }}
.hv-uni {{ letter-spacing: .28em; font-size: .85rem; opacity: .75; animation: aparecer .8s both; }}
.hv-titulo {{ font-size: 2.6rem; font-weight: 700; margin: .25rem 0 .2rem; line-height: 1.15;
             animation: aparecer .9s .2s both; }}
.hv-titulo .grad {{ background: linear-gradient(90deg, {_PLASMA[2]}, {_PLASMA[4]}, {_PLASMA[5]});
                   -webkit-background-clip: text; background-clip: text; color: transparent; }}
.hv-desc {{ opacity: .8; font-size: 1.05rem; animation: aparecer .9s .4s both; }}
.hv-escena {{ display: flex; gap: 34px; align-items: center; justify-content: center; margin: 26px 0 10px;
             flex-wrap: wrap; }}
.hv-horno {{ position: relative; width: 190px; height: 170px; border-radius: 10px;
            animation: color {_DURACION}s ease-out forwards, latido 2.2s {_DURACION}s ease-in-out infinite; }}
.hv-horno::before {{ content: ""; position: absolute; inset: 0; border-radius: 10px;
                    border: 22px solid var(--c); box-shadow: 0 0 34px -6px var(--c); }}
.hv-horno::after {{ content: ""; position: absolute; inset: 22px; border-radius: 4px; background: var(--c);
                   opacity: .55; }}
.hv-temp {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 1;
           font-size: 1.7rem; font-weight: 700; color: #fff; text-shadow: 0 1px 6px #000;
           animation: calentar {_DURACION}s ease-out forwards; counter-reset: t var(--temp); }}
.hv-temp::after {{ content: counter(t) " °C"; background: rgba(0,0,0,.55); padding: 4px 10px; border-radius: 6px; }}
.hv-grafica {{ background: {tema.G_PANEL}; border-radius: 10px; padding: 10px 12px 4px; }}
.hv-grafica path {{ fill: none; stroke: {tema.G_TEMP}; stroke-width: 3; stroke-dasharray: 900;
                   stroke-dashoffset: 900; animation: trazo {_DURACION}s ease-out forwards; }}
.hv-grafica line {{ stroke: {tema.G_SETPOINT}; stroke-width: 1.5; stroke-dasharray: 7 6; }}
.hv-grafica text {{ fill: {tema.G_SETPOINT}; font-size: 12px; }}
.hv-ficha {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 12px; margin: 22px 0 8px; }}
.hv-ficha div {{ background: {tema.G_PANEL}; border: 1px solid rgba(205,214,244,.12); border-radius: 10px;
                padding: 12px 14px; opacity: 0; animation: aparecer .7s both; }}
.hv-ficha small {{ display: block; text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; opacity: .6; }}
.hv-ficha b {{ font-size: 1.15rem; }}
.hv-ficha .destacado {{ border-color: {_PLASMA[4]}; }}
"""


def _html():
    ficha = "".join(
        f'<div class="{"destacado" if rol in ("Autor", "Docente") else ""}" '
        f'style="animation-delay:{0.8 + 0.25 * i:.2f}s"><small>{escape(rol)}</small><b>{escape(nombre)}</b></div>'
        for i, (rol, nombre) in enumerate(creditos.FICHA)
    )
    return f"""
<div class="hv-portada">
  <div class="hv-uni">{escape(creditos.UNIVERSIDAD.upper())} · {escape(creditos.FACULTAD.upper())}</div>
  <div class="hv-titulo">🔥 <span class="grad">{escape(creditos.TITULO)}</span></div>
  <div class="hv-desc">{escape(creditos.DESCRIPCION)}</div>
  <div class="hv-escena">
    <div class="hv-horno"><div class="hv-temp"></div></div>
    <svg class="hv-grafica" width="540" height="160" viewBox="0 0 520 150">
      <line x1="0" y1="18" x2="520" y2="18"></line>
      <text x="6" y="13">Setpoint 1000 °C</text>
      <path d="{_curva()}"></path>
    </svg>
  </div>
  <div class="hv-ficha">{ficha}</div>
</div>
"""


_registro = {"gestor": None, "componente": None}


def _portada(key):
    """La portada como componente (``st.html`` filtra los estilos y el SVG).

    Se registra una vez por runtime de Streamlit, como el monitor. Sin
    aislamiento de estilos: las propiedades CSS animadas (``@property``) no
    funcionan dentro de un shadow DOM.
    """
    gestor = st.components.v2.get_bidi_component_manager()
    if _registro["gestor"] is not gestor:
        _registro["componente"] = st.components.v2.component(
            "portada_horno", html=_html(), css=_css(), isolate_styles=False)
        _registro["gestor"] = gestor
    return _registro["componente"](key=key)


def creditos_en_ventana():
    """Los mismos créditos, para la ventana emergente que se abre desde el simulador."""
    _portada("creditos_ventana")


def mostrar(al_abrir):
    """Dibuja la portada (sin barra lateral); ``al_abrir`` se llama al pulsar el botón."""
    st.html(_OCULTAR_BARRA)
    _portada("portada")
    _, centro, _ = st.columns((2, 1.2, 2))
    centro.button("▶ Abrir el simulador", type="primary", width="stretch", key="b_abrir", on_click=al_abrir)
    st.html(f'<div style="text-align:center;opacity:.5;font-size:.8rem">'
            f'{escape(tema.APP_NOMBRE)} · {escape(tema.APP_VERSION)}</div>')
