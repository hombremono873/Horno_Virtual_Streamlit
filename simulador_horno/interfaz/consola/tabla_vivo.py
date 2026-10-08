"""Panel de estado que se refresca durante la simulación (rich.Live).

Muestra el reloj (tiempo simulado, velocidad y tiempo real), la lectura
instantánea (temperatura, setpoint, u, error), barras de nivel para T y u,
las acciones P/I/D del PID y la configuración vigente. La llama
``Simulador._tabla`` en cada refresco.
"""
from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.control.anti_windup import NOMBRES as NOMBRES_ANTI_WINDUP
from simulador_horno.estilos import tema
from simulador_horno.interfaz.consola.metricas import tabla_metricas

console = Console()


def _lado_a_lado(izq, der):
    """Dos renderables en columnas, sin depender del ancho exacto del terminal."""
    grid = Table.grid(padding=(0, 4))
    grid.add_column()
    grid.add_column()
    grid.add_row(izq, der)
    return grid


def formato_hms(segundos):
    """``3725.4`` -> ``'01:02:05'``."""
    s = int(segundos)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _barra(valor, minimo, maximo, ancho=32, color=tema.C_ACENTO):
    if maximo == minimo:
        frac = 0.0
    else:
        frac = max(0.0, min(1.0, (valor - minimo) / (maximo - minimo)))
    llenos = int(round(frac * ancho))
    barra = Text()
    barra.append("█" * llenos, style=color)
    barra.append("░" * (ancho - llenos), style=tema.C_TENUE)
    return barra


def generar_tabla(t, T, T_set, u, error, pid, horno, acciones, velocidad, t_real, metodo,
                  duracion=None, terminada=False, metricas=None, impulsos=None, impulso_activo=False,
                  aperturas=None, puerta_abierta=False):
    """``duracion``: segundos simulados de la corrida (None = sin límite).

    Al terminar, las barras de nivel se sustituyen por la tabla de
    ``metricas`` de desempeño.
    """
    # -- reloj: tiempo simulado vs. real ------------------------------
    reloj = Table.grid(padding=(0, 2))
    for _ in range(6):
        reloj.add_column()
    simulado = formato_hms(t) if duracion is None else f"{formato_hms(t)} / {formato_hms(duracion)}"
    reloj.add_row(
        Text("Tiempo simulado", style=tema.C_TENUE),
        Text(simulado, style=tema.C_TITULO),
        Text("Velocidad", style=tema.C_TENUE),
        Text(velocidad, style=f"reverse {tema.C_ACENTO}"),
        Text("Tiempo real", style=tema.C_TENUE),
        Text(formato_hms(t_real), style=tema.C_VALOR),
    )

    # -- lectura instantánea --------------------------------------------
    estado = Table(box=box.SIMPLE_HEAD, expand=True, pad_edge=False)
    for col in ("Temperatura (°C)", "Setpoint (°C)", "u(t)", "Error (°C)"):
        estado.add_column(col, justify="right")
    estado.add_row(
        Text(f"{T:8.2f}", style=tema.C_VALOR),
        f"{T_set:8.2f}",
        Text(f"{u:8.3f}", style=tema.C_VALOR),
        Text(f"{error:8.2f}", style=tema.C_AVISO if abs(error) > 1 else tema.C_OK),
    )

    # -- barras -------------------------------------------------------
    barras = Table.grid(padding=(0, 2))
    barras.add_column(justify="right", style=tema.C_TENUE)
    barras.add_column()
    barras.add_column(justify="left", style=tema.C_VALOR)
    t_amb = horno.get("T_amb", 0.0)
    barras.add_row("T → SET", _barra(T, t_amb, max(T_set, t_amb + 1), color=tema.C_ACENTO), f"{T:.1f} °C")
    barras.add_row("u(t) [0, 1]", _barra(u, 0.0, 1.0, color="magenta"), f"{u:.3f}")

    # -- acciones del PID -------------------------------------------
    acc = Table(title="Acciones del PID", box=box.MINIMAL, expand=True, title_style=tema.C_TITULO)
    acc.add_column("Componente", style=tema.C_TENUE)
    acc.add_column("Valor", justify="right", style=tema.C_VALOR)
    acc.add_row("Proporcional (P)", f"{acciones.get('P', 0.0):12.3f}")
    acc.add_row("Integral (I)", f"{acciones.get('I', 0.0):12.3f}")
    acc.add_row("Derivativa (D)", f"{acciones.get('D', 0.0):12.3f}")

    # -- configuración vigente ------------------------------------
    cfg = Table(title="Configuración", box=box.MINIMAL, expand=True, title_style=tema.C_TITULO)
    cfg.add_column("Parámetro", style=tema.C_TENUE)
    cfg.add_column("Valor", justify="right", style=tema.C_VALOR)
    cfg.add_row("Kp / Ki / Kd", f"{pid.get('kp', 0):g} / {pid.get('ki', 0):g} / {pid.get('kd', 0):g}")
    cfg.add_row("Anti-windup", NOMBRES_ANTI_WINDUP[vpid.anti_windup] + (f" ({vpid.restringir_integral:g})" if vpid.anti_windup == "recorte" else ""))
    cfg.add_row("T máx. equilibrio", f"{horno.get('T_max_eq', 0.0):g} °C")
    cfg.add_row("B (ganancia térmica)", f"{horno.get('B', 0.0):.4f} °C/s")
    cfg.add_row("τ (constante de tiempo)", f"{horno.get('tau', 0.0):g} s")
    cfg.add_row("T ambiente", f"{horno.get('T_amb', 0.0):g} °C")
    cfg.add_row("T inicial", f"{horno.get('T_inicial', horno.get('T_amb', 0.0)):g} °C")
    cfg.add_row("Método numérico", metodo)
    cfg.add_row("Δt (paso)", f"{horno.get('dt', 0.1):g} s")

    if terminada:
        ayuda = Text("Analiza las gráficas. Cierra la ventana del monitor o pulsa Ctrl+C "
                     "para volver al menú.", style=tema.C_TENUE, justify="center")
        aviso = Text(f"✓ CORRIDA TERMINADA · {formato_hms(duracion)} simuladas",
                     style=f"reverse {tema.C_OK}", justify="center")
    else:
        ayuda = Text("Cierra la ventana del monitor o pulsa Ctrl+C para detener.",
                     style=tema.C_TENUE, justify="center")
        aviso = Text(justify="center")
        if impulsos is not None:   # perturbación de impulsos activada
            aviso.append(f"Impulsos: {impulsos}", style=tema.C_TENUE)
            if impulso_activo:
                aviso.append("   ⚡ IMPULSO", style=f"reverse {tema.C_AVISO}")
        if aperturas is not None:  # perturbación de puerta activada
            aviso.append(f"   Aperturas de puerta: {aperturas}", style=tema.C_TENUE)
            if puerta_abierta:
                aviso.append("   🚪 PUERTA ABIERTA", style=f"reverse {tema.C_ALERTA}")

    cuerpo = Group(
        Align.center(reloj),
        Align.center(aviso),
        Text(),
        Align.center(estado),
        Text(),
        Align.center(tabla_metricas(metricas) if (terminada and metricas) else barras),
        Text(),
        Align.center(_lado_a_lado(acc, cfg)),
        Text(),
        ayuda,
    )

    return Panel(
        cuerpo,
        title="[b]MONITOR DE SIMULACIÓN[/b] · modo consola",
        subtitle=f"t = {formato_hms(t)} · {velocidad}",
        box=box.HEAVY,
        border_style=tema.C_MARCO_ACENTO,
        padding=(1, 3),
    )
