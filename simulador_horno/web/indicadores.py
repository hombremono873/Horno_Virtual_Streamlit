"""Textos de los indicadores del monitor (sin Streamlit, para poder probarlos)."""
import math
from html import escape

from simulador_horno.modelo.triac import METODOS_INVERSION, MODOS as MODOS_ACTUADOR, energia_kwh
from simulador_horno.numerico.integradores import NOMBRES as NOMBRES_METODOS


def hhmmss(segundos):
    s = int(round(segundos))
    return f"{s // 3600:d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def minutos(segundos):
    return "—" if segundos is None else f"{segundos / 60:.1f} min"


def con_signo(valor, decimales=1):
    """``+12.3``; sin "−0.0" cuando el valor redondea a cero."""
    if abs(valor) < 0.5 * 10 ** -decimales:
        valor = 0.0
    return f"{valor:+.{decimales}f}" if valor else f"{0.0:.{decimales}f}"


def indicadores(sim, en_vivo_modo, m):
    """Lista de ``(etiqueta, valor)``; ``m`` son las métricas actuales (o None)."""
    factor = sim.config.simulacion.velocidad if en_vivo_modo else "máxima"
    return [
        ("Tiempo simulado", hhmmss(sim.t)),
        ("Temperatura", f"{sim.T:.1f} °C"),
        ("Setpoint", f"{sim.config.horno.T_SET:.0f} °C"),
        ("Error", f"{con_signo(sim.error)} °C"),
        ("Control u", f"{sim.u:.3f}"),
        ("Sobrepaso", "—" if m is None else f"{m.sobrepaso_pct:.2f} %"),
        ("Tiempo al 90 %", "—" if m is None else minutos(m.t90)),
        ("Factor activo", factor),
    ]


def tablero(sim, en_vivo_modo, m):
    """Indicadores agrupados para la pestaña de valores: ``[(grupo, [(etiqueta, valor)...])...]``."""
    base = dict(indicadores(sim, en_vivo_modo, m))
    h, pid = sim.historial, sim.config.pid
    P, I, D = (h.proporcionales[-1], h.integrales[-1], h.derivativos[-1]) if len(h) else (0.0, 0.0, 0.0)
    return [
        ("Proceso", [(e, base[e]) for e in ("Tiempo simulado", "Temperatura", "Setpoint", "Error", "Control u")]),
        ("Controlador PID", [
            ("Aporte P", f"{P:+.3f}"), ("Aporte I", f"{I:+.3f}"), ("Aporte D", f"{D:+.3f}"),
            ("Ganancias", f"{pid.KP:g} · {pid.KI:g} · {pid.KD:g}"),
        ]),
        ("Desempeño", [
            ("Sobrepaso", base["Sobrepaso"]), ("Tiempo al 90 %", base["Tiempo al 90 %"]),
            ("Establecimiento ±1 %", "—" if m is None else minutos(m.t_establecimiento)),
            ("IAE", "—" if m is None else f"{m.iae / 60:,.0f} °C·min"),
        ]),
        ("Ejecución", [
            ("Factor activo", base["Factor activo"]),
            ("Método", NOMBRES_METODOS[sim.metodo]),
            ("Δt", f"{sim.config.horno.DT:g} s"),
            ("Impulsos · aperturas", f"{sim.impulsos} · {sim.aperturas}"),
        ]),
        ("Actuador", _actuador(sim)),
        ("Horno (inercia térmica)", _inercia(sim)),
    ]


def control(pid):
    """Texto del modo de control: 'Manual 60 %' o 'Automático' (con su límite)."""
    if pid.modo_control == "manual":
        return f"Manual {pid.potencia_manual * 100:.1f} %"
    return "Automático" if pid.limite_potencia >= 1.0 else f"Automático (límite {pid.limite_potencia * 100:.0f} %)"


def _actuador(sim):
    act = sim.config.actuador
    filas = [
        ("Control", control(sim.config.pid)),
        ("Actuador", MODOS_ACTUADOR[act.modo]),
        ("Potencia pedida (u)", f"{sim.u * 100:.1f} %"),
        ("Potencia entregada", f"{sim.fraccion * 100:.1f} %"),
        ("Ángulo de disparo α", "—" if math.isnan(sim.alfa) else f"{sim.alfa:.2f}°"),
        ("Potencia eléctrica", f"{sim.potencia_w:,.0f} W"),
        ("Corriente", f"{math.sqrt(sim.potencia_w / act.R):.2f} A" if sim.potencia_w > 0 else "0.00 A"),
        ("Energía consumida", f"{energia_kwh(sim.energia_j):.3f} kWh"),
    ]
    if act.modo == "triac_compensado":
        filas.append((f"Iteraciones ({METODOS_INVERSION[act.metodo]})", f"{sim.iteraciones}"))
    return filas


def _inercia(sim):
    """Capacidad térmica y pérdidas que implican la potencia nominal, B y τ."""
    horno, act = sim.config.horno, sim.config.actuador
    C = act.potencia_nominal / horno.B if horno.B else math.inf      # J/°C
    return [
        ("Constante de tiempo τ", f"{horno.TAU:g} s ({horno.TAU / 60:.0f} min)"),
        ("Ganancia térmica B", f"{horno.B:.4f} °C/s"),
        ("Capacidad térmica C = P/B", f"{C:,.0f} J/°C"),
        ("Pérdidas h = C/τ", f"{C / horno.TAU:.2f} W/°C"),
    ]


def estado(sim, en_vivo):
    """Avisos de la corrida como fragmentos HTML (texto escapado)."""
    avisos = []
    if sim.terminada:
        avisos.append('<b class="ok">✅ Corrida terminada</b>')
    elif en_vivo:
        avisos.append('<b class="vivo">● Simulando en vivo</b>')
    elif len(sim.historial):
        avisos.append("⏸ En pausa")
    else:
        avisos.append("Pulsa <b>▶ Iniciar</b> (en vivo) o <b>▶ Simular</b> (corrida completa) en la barra lateral.")
    pid = sim.config.pid
    if pid.modo_control == "manual" or pid.limite_potencia < 1.0:
        avisos.append(f'<b class="alerta">{escape(control(pid)).upper()}</b>')
    if sim.impulso_activo:
        avisos.append('<b class="alerta">⚡ IMPULSO en la medición</b>')
    if sim.puerta_abierta:
        avisos.append('<b class="alerta">🚪 Puerta abierta</b>')
    if sim.config.perturbaciones.flag_error:
        avisos.append(escape(f"Impulsos: {sim.impulsos}"))
    if sim.config.perturbaciones.puerta:
        avisos.append(escape(f"Aperturas de puerta: {sim.aperturas}"))
    return avisos
