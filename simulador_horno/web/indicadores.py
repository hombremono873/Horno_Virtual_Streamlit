"""Textos de los indicadores del monitor (sin Streamlit, para poder probarlos)."""
from html import escape


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
    if sim.impulso_activo:
        avisos.append('<b class="alerta">⚡ IMPULSO en la medición</b>')
    if sim.puerta_abierta:
        avisos.append('<b class="alerta">🚪 Puerta abierta</b>')
    if sim.config.perturbaciones.flag_error:
        avisos.append(escape(f"Impulsos: {sim.impulsos}"))
    if sim.config.perturbaciones.puerta:
        avisos.append(escape(f"Aperturas de puerta: {sim.aperturas}"))
    return avisos
