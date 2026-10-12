"""Animación del horno de joyería: dibujo en corte que reacciona a la simulación.

Un SVG fijo (horno, resistencias, cilindros de revestimiento, puerta, termopar,
interruptor, controlador PID y triac) montado UNA vez como componente; en cada
refresco Python solo envía unos pocos números y el navegador cambia colores y
textos con transiciones CSS suaves (sin parpadeo).

- La cámara toma el COLOR DE INCANDESCENCIA de su temperatura, el que usan
  los joyeros para "leer" el horno a ojo.
- Las resistencias brillan según la potencia que LLEGA (no la pedida).
- El controlador muestra PV (lo que lee el termopar), SV (setpoint) y OUT
  (la u del PID), con las luces OUT, MAN y AL, como los controladores reales.
"""
import json

import streamlit as st

from simulador_horno.web import indicadores as ind

# (°C, color) de la incandescencia: por debajo de ~500 °C el horno no brilla
_INCANDESCENCIA = (
    (450, (0x2a, 0x1c, 0x1a)),
    (550, (0x4a, 0x10, 0x08)),
    (650, (0x7a, 0x14, 0x08)),
    (750, (0xa8, 0x22, 0x0c)),
    (850, (0xd2, 0x3c, 0x12)),
    (950, (0xec, 0x66, 0x1a)),
    (1050, (0xf7, 0x96, 0x2b)),
    (1150, (0xfb, 0xbf, 0x4a)),
    (1250, (0xfd, 0xe2, 0x7a)),
    (1350, (0xff, 0xf4, 0xc8)),
)


def color_incandescencia(T):
    """Color (hex) de un cuerpo a T °C, interpolando la escala de incandescencia."""
    tabla = _INCANDESCENCIA
    if T <= tabla[0][0]:
        r, g, b = tabla[0][1]
    elif T >= tabla[-1][0]:
        r, g, b = tabla[-1][1]
    else:
        for (t0, c0), (t1, c1) in zip(tabla, tabla[1:]):
            if t0 <= T <= t1:
                k = (T - t0) / (t1 - t0)
                r, g, b = (round(a + k * (b_ - a)) for a, b_ in zip(c0, c1))
                break
    return f"#{r:02x}{g:02x}{b:02x}"


def datos_horno(sim):
    """Lo que necesita el dibujo en este instante (pocos números y textos)."""
    act, pid, horno = sim.config.actuador, sim.config.pid, sim.config.horno
    fraccion = sim.fraccion if act.encendido else 0.0
    # una resistencia que conduce está más caliente que la cámara
    T_resistencia = max(sim.T, 600.0 + 700.0 * fraccion) if fraccion > 0 else sim.T
    medida = horno.T_SET - sim.error
    return {
        "camara": color_incandescencia(sim.T),
        "resistencia": color_incandescencia(T_resistencia),
        "brillo_res": round(2 + 16 * fraccion, 1),
        "brillo_cam": round(max(0.0, min(1.0, (sim.T - 450) / 800)) * 40, 1),
        "pv": f"{medida:.0f}",
        "sv": f"{horno.T_SET:.0f}",
        "out": round(100 * sim.u, 1),
        "entregada": round(100 * fraccion, 1),
        "temp": f"{sim.T:.0f} °C",
        "tiempo": ind.hhmmss(sim.t),
        "encendido": act.encendido,
        "conduce": fraccion > 0,
        "manual": pid.modo_control == "manual",
        "alarma": bool(sim.impulso_activo or sim.puerta_abierta),
        "puerta": bool(sim.puerta_abierta),
        "control": ind.control(pid),
    }


_HTML = """
<div class="hv-anim">
<svg viewBox="0 0 1000 560" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hv-ladrillo" width="40" height="20" patternUnits="userSpaceOnUse">
      <rect width="40" height="20" fill="#7a5f4b"/>
      <path d="M0 0H40M0 10H40M20 0V10M0 10V20M40 10V20" stroke="#5b4636" stroke-width="1.5"/>
    </pattern>
  </defs>
  <!-- horno -->
  <rect x="40" y="70" width="520" height="420" rx="14" fill="#3b3f4a" stroke="#5b6170" stroke-width="3"/>
  <rect x="70" y="100" width="460" height="360" rx="6" fill="url(#hv-ladrillo)"/>
  <rect class="hv-camara" x="120" y="150" width="300" height="260" rx="6"/>
  <polyline class="hv-res" points="132,165 142,180 132,195 142,210 132,225 142,240 132,255 142,270 132,285 142,300 132,315 142,330 132,345 142,360 132,375 142,390"/>
  <polyline class="hv-res" points="408,165 398,180 408,195 398,210 408,225 398,240 408,255 398,270 408,285 398,300 408,315 398,330 408,345 398,360 408,375 398,390"/>
  <polyline class="hv-res" points="150,160 165,170 180,160 195,170 210,160 225,170 240,160 255,170 270,160 285,170 300,160 315,170 330,160 345,170 360,160 375,170 390,160"/>
  <g class="hv-flask">
    <rect x="165" y="300" width="52" height="100" rx="4"/><ellipse cx="191" cy="300" rx="26" ry="7"/>
    <rect x="244" y="300" width="52" height="100" rx="4"/><ellipse cx="270" cy="300" rx="26" ry="7"/>
    <rect x="323" y="300" width="52" height="100" rx="4"/><ellipse cx="349" cy="300" rx="26" ry="7"/>
  </g>
  <text class="hv-temp" x="270" y="250" text-anchor="middle"></text>
  <!-- calor que sale por la puerta abierta -->
  <g class="hv-ondas">
    <path d="M440 380 q15 -30 0 -60 q-15 -30 0 -60 q15 -30 0 -60"/>
    <path d="M470 390 q15 -30 0 -60 q-15 -30 0 -60 q15 -30 0 -60"/>
    <path d="M500 380 q15 -30 0 -60 q-15 -30 0 -60 q15 -30 0 -60"/>
  </g>
  <g class="hv-puerta"><rect x="420" y="140" width="45" height="280" rx="4" fill="#4a505d" stroke="#6b7282" stroke-width="2"/>
    <rect x="452" y="260" width="8" height="40" rx="3" fill="#aab0bd"/></g>
  <!-- termopar -->
  <line x1="300" y1="40" x2="300" y2="205" stroke="#c9ccd3" stroke-width="5"/>
  <circle cx="300" cy="207" r="5" fill="#e6e9ef"/>
  <text x="310" y="58" class="hv-rotulo">Termopar</text>
  <!-- interruptor de potencia -->
  <g class="hv-interruptor"><rect x="70" y="462" width="74" height="22" rx="11"/><circle cx="85" cy="473" r="8"/>
    <text x="155" y="478" class="hv-rotulo hv-onoff"></text></g>
  <rect x="80" y="490" width="60" height="20" fill="#2b2e36"/><rect x="460" y="490" width="60" height="20" fill="#2b2e36"/>
  <text x="300" y="540" text-anchor="middle" class="hv-rotulo">Horno de joyería (corte)</text>
  <!-- controlador PID -->
  <rect x="610" y="70" width="360" height="250" rx="10" fill="#15171c" stroke="#454a55" stroke-width="2"/>
  <text x="790" y="96" text-anchor="middle" class="hv-rotulo">CONTROLADOR PID</text>
  <text x="635" y="140" class="hv-etq">PV</text><text x="945" y="150" text-anchor="end" class="hv-pv"></text>
  <text x="635" y="200" class="hv-etq">SV</text><text x="945" y="205" text-anchor="end" class="hv-sv"></text>
  <text x="635" y="240" class="hv-etq">OUT</text><text x="945" y="240" text-anchor="end" class="hv-out"></text>
  <rect x="635" y="250" width="310" height="12" rx="6" fill="#2b2e36"/>
  <rect class="hv-barra" x="635" y="250" width="0" height="12" rx="6"/>
  <circle class="hv-led-out" cx="660" cy="292" r="8"/><text x="674" y="297" class="hv-etq-led">OUT</text>
  <circle class="hv-led-man" cx="760" cy="292" r="8"/><text x="774" y="297" class="hv-etq-led">MAN</text>
  <circle class="hv-led-al" cx="860" cy="292" r="8"/><text x="874" y="297" class="hv-etq-led">AL</text>
  <!-- triac / relé de estado sólido -->
  <path d="M700 320 V360" class="hv-cable"/><path d="M650 405 H560" class="hv-cable hv-cable-pot"/>
  <path d="M800 405 H960" class="hv-cable"/><text x="965" y="400" class="hv-rotulo" text-anchor="end">Red 220 VCA</text>
  <rect x="650" y="360" width="150" height="90" rx="8" fill="#23262e" stroke="#454a55" stroke-width="2"/>
  <text x="725" y="392" text-anchor="middle" class="hv-rotulo">TRIAC</text>
  <circle class="hv-led-triac" cx="725" cy="420" r="9"/>
  <text x="725" y="480" text-anchor="middle" class="hv-entregada hv-rotulo"></text>
  <text x="790" y="530" text-anchor="middle" class="hv-estado hv-rotulo"></text>
</svg>
</div>
"""

_CSS = """
.hv-anim { --camara: #2a1c1a; --resistencia: #2a1c1a; --brillo-res: 2px; --brillo-cam: 0px; max-width: 1100px; margin: 0 auto; }
.hv-anim svg { width: 100%; height: auto; font-family: "Source Sans Pro", "Segoe UI", sans-serif; }
.hv-camara { fill: var(--camara); filter: drop-shadow(0 0 var(--brillo-cam) var(--camara));
             transition: fill .8s linear, filter .8s linear; }
.hv-res { fill: none; stroke: var(--resistencia); stroke-width: 5; stroke-linejoin: round;
          filter: drop-shadow(0 0 var(--brillo-res) var(--resistencia)); transition: stroke .5s, filter .5s; }
.hv-flask rect, .hv-flask ellipse { fill: #8d8478; stroke: #5f574d; stroke-width: 1.5;
          filter: drop-shadow(0 0 2px var(--camara)); transition: filter .8s; }
.hv-temp { font-size: 30px; font-weight: 700; fill: #fff; paint-order: stroke; stroke: rgba(0,0,0,.6); stroke-width: 4px; }
.hv-rotulo { font-size: 15px; fill: #cdd6f4; }
.hv-etq { font-size: 18px; fill: #8b92a5; font-weight: 600; }
.hv-etq-led { font-size: 14px; fill: #8b92a5; }
.hv-pv { font: 700 54px "Consolas", "Courier New", monospace; fill: #ff453a; }
.hv-sv { font: 700 34px "Consolas", "Courier New", monospace; fill: #32d74b; }
.hv-out { font: 700 22px "Consolas", "Courier New", monospace; fill: #ffd60a; }
.hv-barra { fill: #ffd60a; transition: width .3s; }
.hv-cable { stroke: #6b7282; stroke-width: 4; fill: none; }
.hv-cable-pot { transition: stroke .3s; }
.hv-anim .hv-led-out, .hv-anim .hv-led-man, .hv-anim .hv-led-al, .hv-anim .hv-led-triac { fill: #30333b; transition: fill .2s; }
.hv-anim.conduce .hv-led-out { fill: #ffd60a; animation: hv-parpadeo .5s steps(2) infinite; }
.hv-anim.conduce .hv-led-triac { fill: #ff9f0a; filter: drop-shadow(0 0 8px #ff9f0a); }
.hv-anim.conduce .hv-cable-pot { stroke: #ff9f0a; }
.hv-anim.manual .hv-led-man { fill: #ff9f0a; }
.hv-anim.alarma .hv-led-al { fill: #ff453a; animation: hv-parpadeo .4s steps(2) infinite; }
.hv-puerta { transition: transform .7s ease; }
.hv-anim.puerta .hv-puerta { transform: translateY(-190px); }
.hv-ondas path { fill: none; stroke: var(--camara); stroke-width: 4; stroke-linecap: round; opacity: 0; }
.hv-anim.puerta .hv-ondas path { animation: hv-calor 1.6s ease-in infinite; }
.hv-anim.puerta .hv-ondas path:nth-child(2) { animation-delay: .5s; }
.hv-anim.puerta .hv-ondas path:nth-child(3) { animation-delay: 1s; }
.hv-interruptor rect { fill: #34c759; transition: fill .3s; }
.hv-interruptor circle { fill: #fff; transform: translateX(44px); transition: transform .3s; }
.hv-anim.apagado .hv-interruptor rect { fill: #ff453a; }
.hv-anim.apagado .hv-interruptor circle { transform: translateX(0); }
.hv-estado { font-size: 17px; font-weight: 700; fill: #ffd60a; }
@keyframes hv-parpadeo { 50% { opacity: .25; } }
@keyframes hv-calor { 0% { opacity: 0; transform: translateY(20px); } 30% { opacity: .9; }
                      100% { opacity: 0; transform: translateY(-70px); } }
"""

_JS = """
export default function (component) {
    const { data, parentElement } = component;
    let raiz = parentElement.querySelector(".hv-anim");
    if (!raiz) { parentElement.insertAdjacentHTML("beforeend", HTML); raiz = parentElement.querySelector(".hv-anim"); }
    if (!data) return;
    const s = raiz.style;
    s.setProperty("--camara", data.camara);
    s.setProperty("--resistencia", data.resistencia);
    s.setProperty("--brillo-res", data.brillo_res + "px");
    s.setProperty("--brillo-cam", data.brillo_cam + "px");
    for (const clase of ["conduce", "manual", "alarma", "puerta"]) raiz.classList.toggle(clase, !!data[clase]);
    raiz.classList.toggle("apagado", !data.encendido);
    const texto = (sel, t) => { raiz.querySelector(sel).textContent = t; };
    texto(".hv-pv", data.pv); texto(".hv-sv", data.sv);
    texto(".hv-out", data.out.toFixed(1) + " %");
    texto(".hv-temp", data.temp);
    texto(".hv-onoff", data.encendido ? "ENCENDIDO" : "APAGADO");
    texto(".hv-entregada", "Entrega " + data.entregada.toFixed(1) + " %");
    texto(".hv-estado", (data.encendido ? "" : "⏻ HORNO APAGADO · ") + data.control + " · " + data.tiempo);
    raiz.querySelector(".hv-barra").setAttribute("width", (310 * Math.min(100, data.out) / 100).toFixed(1));
}
"""

_registro = {"gestor": None, "componente": None}


def _componente():
    """Registrado una vez por runtime de Streamlit (como el monitor)."""
    gestor = st.components.v2.get_bidi_component_manager()
    if _registro["gestor"] is not gestor:
        js = "const HTML = " + json.dumps(_HTML) + ";\n" + _JS
        _registro["componente"] = st.components.v2.component("horno_animado", css=_CSS, js=js,
                                                             isolate_styles=False)
        _registro["gestor"] = gestor
    return _registro["componente"]


def mostrar(sim):
    return _componente()(key="horno_animado", data=datos_horno(sim))
