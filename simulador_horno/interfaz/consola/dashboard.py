"""Dashboard: tabla comparativa de corridas guardadas (rich).

Cada corrida es un CSV leído con ``simulacion.resultados.leer``. Las
columnas son las corridas (A, B, C...) y las filas, su configuración y
sus métricas, para comparar de un vistazo qué cambió y con qué efecto.
"""
from pathlib import Path

from rich import box
from rich.table import Table
from rich.text import Text

from simulador_horno.configuracion import limites
from simulador_horno.estilos import tema
from simulador_horno.numerico.integradores import NOMBRES as NOMBRES_METODOS
from simulador_horno.simulacion.resultados import metricas_guardadas, numero

LETRAS = "ABCDEFG"


def etiqueta(parametros):
    """Resumen corto de una corrida para listas y leyendas."""
    fecha = parametros.get("fecha", "")[5:16].replace("-", "/")   # MM/DD HH:MM
    metodo = NOMBRES_METODOS.get(parametros.get("metodo"), parametros.get("metodo", "?"))
    return (f"{fecha} · {metodo} Δt {parametros.get('dt', '?')} · {parametros.get('anti_windup', '?')} · "
            f"Kp {parametros.get('KP', '?')} Ki {parametros.get('KI', '?')} Kd {parametros.get('KD', '?')}")


def _perturbaciones(parametros):
    activas = [nombre for atributo, nombre, _ in limites.PERTURBACIONES
               if parametros.get(f"perturbacion_{atributo}") == "si"]
    return ", ".join(activas) or "ninguna"


def _min(valor):
    return "—" if valor is None else f"{valor / 60:.1f} min"


def tabla_comparativa(corridas):
    """``corridas``: lista de ``(ruta, parametros)`` en el orden A, B, C..."""
    t = Table(title="Comparación de corridas", title_style=tema.C_TITULO,
              box=box.SIMPLE_HEAD, pad_edge=False)
    t.add_column("", style=tema.C_TENUE)
    for i, _ in enumerate(corridas):
        t.add_column(Text(LETRAS[i], style=f"bold {tema.G_CORRIDAS[i]}"), justify="right")

    def fila(nombre, valores, estilo=tema.C_VALOR):
        t.add_row(nombre, *[Text(v, style=estilo) for v in valores])

    ps = [p for _, p in corridas]
    ms = [metricas_guardadas(p) for p in ps]
    fila("Método", [NOMBRES_METODOS.get(p.get("metodo"), "?") for p in ps], tema.C_TEXTO)
    fila("Δt (s)", [p.get("dt", "?") for p in ps], tema.C_TEXTO)
    fila("Kp / Ki / Kd", [f"{p.get('KP')} / {p.get('KI')} / {p.get('KD')}" for p in ps], tema.C_TEXTO)
    fila("Anti-windup", [p.get("anti_windup", "?") for p in ps], tema.C_TEXTO)
    fila("T inicial (°C)", [p.get("T_INICIAL", p.get("T_AMB", "?")) for p in ps], tema.C_TEXTO)
    fila("Perturbaciones", [_perturbaciones(p) for p in ps], tema.C_TEXTO)
    fila("Duración / completa", [f"{p.get('duracion_h') or 'sin límite'} h · {p.get('corrida_completa', '?')}"
                                 for p in ps], tema.C_TEXTO)
    t.add_section()
    fila("Sobrepaso", [f"{m.get('sobrepaso_pct') or 0:.2f} %  ({m.get('sobrepaso_c') or 0:.1f} °C)" for m in ms])
    fila("Tiempo de subida", [_min(m.get("t_subida")) for m in ms])
    fila("Tiempo al 90 %", [_min(m.get("t90")) for m in ms])
    fila("Establecimiento ±1 %", [_min(m.get("t_establecimiento")) for m in ms])
    fila("Error final", [f"{m.get('error_final') or 0:+.2f} °C" for m in ms])
    fila("IAE (°C·min)", [f"{(m.get('iae') or 0) / 60:,.0f}" for m in ms])
    fila("ISE (°C²·min)", [f"{(m.get('ise') or 0) / 60:,.0f}" for m in ms])
    t.add_section()
    fila("Archivo", [Path(r).name[:17] for r, _ in corridas], tema.C_TENUE)
    return t


def nota_comparacion(corridas):
    duraciones = {numero(p.get("metrica_duracion", "")) for _, p in corridas}
    if len(duraciones) > 1:
        return Text("Atención: las corridas tienen duraciones distintas; IAE e ISE no son comparables.",
                    style=tema.C_AVISO)
    return Text("Compara cambiando una sola cosa a la vez. Menor IAE/ISE = mejor seguimiento.",
                style=tema.C_TENUE)
