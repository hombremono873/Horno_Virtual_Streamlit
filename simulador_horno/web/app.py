"""Página de Streamlit del simulador.

Estado por usuario: cada sesión guarda en ``st.session_state`` su propio
``Simulador`` (con su configuración, PID, perturbaciones e historial) y su
``EjecucionEnVivo``. No hay estado global mutable: lo que hace un
estudiante no afecta a otro.

Dos modos:

- **Corrida completa**: simula la duración elegida de una vez y la muestra;
  puede superponer la corrida anterior para comparar sintonías.
- **En vivo**: un fragmento (``st.fragment(run_every=...)``) avanza los
  pasos que tocan según la velocidad y redibuja solo el monitor.

Los widgets de la barra lateral escriben en ``sim.config`` en cada
ejecución; el método numérico y la duración se aplican al reiniciar.
"""
import streamlit as st

from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import Configuracion
from simulador_horno.control.anti_windup import NOMBRES as NOMBRES_ANTI_WINDUP
from simulador_horno.estilos import tema
from simulador_horno.numerico.integradores import METODOS, NOMBRES as NOMBRES_METODOS
from simulador_horno.simulacion.simulador import Simulador
from simulador_horno.web import datos, graficas, monitor
from simulador_horno.web import indicadores as ind
from simulador_horno.web.ejecucion import EjecucionEnVivo

DEFECTO = Configuracion()
MODOS = ("Corrida completa", "En vivo")
DURACIONES = limites.DURACIONES_HORAS
SEMILLA_DEFECTO = 2026


# ======================================================================
# Estado de la sesión
# ======================================================================
def _estado():
    ss = st.session_state
    if "sim" not in ss:
        ss.sim = Simulador(Configuracion())
        ss.vivo = EjecucionEnVivo(ss.sim)
        ss.en_vivo = False
        ss.anterior = None
    return ss


def _aplicar_widgets(sim):
    """Copia los valores de la barra lateral a la configuración del simulador."""
    ss = st.session_state
    c = sim.config
    for campo in ("T_AMB", "T_SET", "T_MAX_EQ", "T_INICIAL", "TAU", "DT"):
        setattr(c.horno, campo, float(ss[f"w_{campo}"]))
    for campo in ("KP", "KI", "KD", "anti_windup", "restringir_integral"):
        setattr(c.pid, campo, ss[f"w_{campo}"])
    for atributo, _, _ in limites.PERTURBACIONES:
        setattr(c.perturbaciones, atributo, bool(ss[f"w_{atributo}"]))
    c.perturbaciones.tasa_impulsos_hora = float(ss.w_tasa_impulsos_hora)
    c.simulacion.metodo = ss.w_metodo
    c.simulacion.duracion_horas = ss.w_duracion
    c.simulacion.velocidad = ss.w_velocidad
    sim.semilla = int(ss.w_semilla) if ss.w_fijar_semilla else None


# ---- acciones de los botones (corren antes de dibujar la página) ------
def _simular():
    ss = _estado()
    _aplicar_widgets(ss.sim)
    if ss.sim.config.simulacion.duracion_horas is None:
        return
    if len(ss.sim.historial) > 1:
        ss.anterior = graficas.instantanea(ss.sim.historial)
    ss.sim.reiniciar()
    ss.vivo.reiniciar()
    ss.sim.completar()


def _alternar_vivo():
    ss = _estado()
    _aplicar_widgets(ss.sim)
    if ss.en_vivo:
        ss.en_vivo = False
        ss.vivo.pausar()
        return
    if ss.sim.terminada or len(ss.sim.historial) == 0:
        ss.sim.reiniciar()
        ss.vivo.reiniciar()
    ss.en_vivo = True


def _reiniciar():
    ss = _estado()
    _aplicar_widgets(ss.sim)
    ss.en_vivo = False
    ss.sim.reiniciar()
    ss.vivo.reiniciar()


def _cambio_de_modo():
    ss = _estado()
    ss.en_vivo = False
    ss.vivo.pausar()


# ======================================================================
# Barra lateral
# ======================================================================
def _formato_duracion(horas):
    if horas is None:
        return "Sin límite (solo en vivo)"
    return f"{horas * 60:g} min" if horas < 1 else f"{horas:g} h"


def _barra_lateral(ss):
    sim = ss.sim
    with st.sidebar:
        st.markdown(f"**{tema.APP_NOMBRE}**  \n{tema.INSTITUCION}")
        modo = st.segmented_control("Modo", MODOS, default=MODOS[1], required=True,
                                    key="w_modo", on_change=_cambio_de_modo, width="stretch")

        with st.expander("Horno", expanded=True):
            h = DEFECTO.horno
            st.number_input("Temperatura ambiente T_AMB (°C)", -20.0, 60.0, h.T_AMB, 1.0, key="w_T_AMB")
            st.number_input("Setpoint T_SET (°C)", 50.0, 1500.0, h.T_SET, 10.0, key="w_T_SET",
                            help="En vivo se puede cambiar a mitad de la corrida.")
            st.number_input("Equilibrio a potencia plena T_MAX_EQ (°C)", 100.0, 3000.0, h.T_MAX_EQ, 10.0,
                            key="w_T_MAX_EQ", help="Temperatura a la que llega el horno con u = 1.")
            st.number_input("Temperatura inicial (°C)", -20.0, 1500.0, h.T_INICIAL, 10.0, key="w_T_INICIAL",
                            help="Igual a T_AMB = arranque en frío. Se aplica al reiniciar.")
            st.number_input("Constante de tiempo τ (s)", 100.0, 20000.0, float(h.TAU), 100.0, key="w_TAU")
            st.caption(f"Ganancia térmica calculada **B = (T_MAX_EQ − T_AMB)/τ = {sim.config.horno.B:.4f} °C/s**")

        with st.expander("Controlador PID", expanded=True):
            p = DEFECTO.pid
            st.number_input("Kp", 0.0, 10000.0, float(p.KP), 10.0, key="w_KP")
            st.number_input("Ki", 0.0, 1000.0, float(p.KI), 1.0, key="w_KI")
            st.number_input("Kd", 0.0, 1000.0, float(p.KD), 1.0, key="w_KD")
            st.selectbox("Anti-windup", list(NOMBRES_ANTI_WINDUP), format_func=NOMBRES_ANTI_WINDUP.get,
                         index=list(NOMBRES_ANTI_WINDUP).index(p.anti_windup), key="w_anti_windup")
            st.slider("Factor de recorte de la integral", 0.0, 1.0, p.restringir_integral, 0.05,
                      key="w_restringir_integral",
                      disabled=st.session_state.get("w_anti_windup", p.anti_windup) != "recorte",
                      help=f"Solo en modo «Recorte»: si la integral supera {limites.UMBRAL_INTEGRAL} "
                           "se multiplica por este factor.")

        with st.expander("Perturbaciones"):
            for tipo in ("medición", "horno"):
                st.caption(f"Sobre la **{tipo}**")
                for atributo, nombre, de in limites.PERTURBACIONES:
                    if de == tipo:
                        st.toggle(nombre, getattr(DEFECTO.perturbaciones, atributo), key=f"w_{atributo}")
            st.slider("Impulsos por hora simulada", 0.0, 60.0, float(DEFECTO.perturbaciones.tasa_impulsos_hora),
                      1.0, key="w_tasa_impulsos_hora",
                      disabled=not st.session_state.get("w_flag_error", False))

        with st.expander("Simulación", expanded=True):
            s = DEFECTO.simulacion
            st.selectbox("Duración (tiempo simulado)", DURACIONES, index=DURACIONES.index(s.duracion_horas),
                         format_func=_formato_duracion, key="w_duracion")
            st.selectbox("Velocidad (en vivo)", list(limites.VELOCIDADES),
                         index=list(limites.VELOCIDADES).index(s.velocidad), key="w_velocidad",
                         disabled=modo != "En vivo",
                         help="Tiempo simulado por segundo real. No cambia la física: Δt es el mismo.")
            st.selectbox("Método numérico", list(METODOS), format_func=NOMBRES_METODOS.get,
                         index=list(METODOS).index(s.metodo), key="w_metodo")
            st.number_input("Paso de integración Δt (s)", 0.01, 120.0, DEFECTO.horno.DT, 0.05,
                            format="%.2f", key="w_DT")
            st.toggle("Fijar semilla (corridas repetibles)", False, key="w_fijar_semilla",
                      help="Con la misma semilla, las perturbaciones aleatorias se repiten exactamente.")
            st.number_input("Semilla", 0, 2**31 - 1, SEMILLA_DEFECTO, 1, key="w_semilla",
                            disabled=not st.session_state.get("w_fijar_semilla", False))

        st.divider()
        if modo == "Corrida completa":
            sin_limite = st.session_state.get("w_duracion", s.duracion_horas) is None
            st.button("▶ Simular", type="primary", width="stretch", key="b_simular",
                      on_click=_simular, disabled=sin_limite)
            if sin_limite:
                st.caption("Elige una duración para la corrida completa.")
            st.toggle("Superponer la corrida anterior", True, key="w_superponer")
        else:
            c1, c2 = st.columns(2)
            c1.button("⏸ Pausar" if ss.en_vivo else "▶ Iniciar", type="primary", width="stretch",
                      key="b_vivo", on_click=_alternar_vivo)
            c2.button("↺ Reiniciar", width="stretch", key="b_reiniciar", on_click=_reiniciar)
    return modo


# ======================================================================
# Pestañas: monitor (gráficas) e indicadores (valores)
# ======================================================================
def _monitor(ss, modo):
    """Avanza la corrida (si está en vivo) y actualiza el lienzo."""
    sim = ss.sim
    if ss.en_vivo:
        ss.vivo.refresco()
        nuevos = ss.vivo.impulsos_nuevos()
        if nuevos:
            st.toast(f"Impulso en la medición ({sim.impulsos} en la corrida)", icon="⚡")
    en_vivo_modo = modo == "En vivo"
    anterior = ss.anterior if (not en_vivo_modo and st.session_state.get("w_superponer")) else None
    # en vivo: ventana deslizante de las últimas MUESTRAS_MONITOR muestras y escala de
    # los últimos minutos; en una corrida completa, toda la corrida
    figura = graficas.figura_monitor(
        sim.historial, sim.duracion, anterior, T_amb=sim.config.horno.T_AMB,
        ventana_min=tema.G_VENTANA_ESCALA_MIN if en_vivo_modo else None,
        muestras_visibles=limites.MUESTRAS_MONITOR if en_vivo_modo else None,
    )
    monitor.lienzo(figura, [f"⏱ {ind.hhmmss(sim.t)}"] + ind.estado(sim, ss.en_vivo))
    if ss.en_vivo and sim.terminada:
        ss.en_vivo = False
        st.rerun()   # detiene el refresco automático y actualiza los botones


def _tablero(ss, modo):
    """Solo muestra los valores (el monitor es quien avanza la corrida)."""
    sim = ss.sim
    monitor.tablero(ind.tablero(sim, modo == "En vivo", sim.metricas()), ind.estado(sim, ss.en_vivo))


# ======================================================================
# Resultados
# ======================================================================
def _resultados(sim):
    m = sim.metricas()
    if m is None:
        return
    st.subheader("Desempeño de la corrida" if sim.terminada else "Desempeño (corrida incompleta)")
    filas = [
        ("Sobrepaso", f"{m.sobrepaso_c:.2f} °C  ({m.sobrepaso_pct:.2f} % del salto)"),
        ("Tiempo de subida (10 % → 90 %)", ind.minutos(m.t_subida)),
        ("Tiempo al 90 %", ind.minutos(m.t90)),
        ("Establecimiento (±1 %)", ind.minutos(m.t_establecimiento)),
        ("Error final", f"{m.error_final:+.3f} °C"),
        ("IAE = ∫|e| dt", f"{m.iae / 60:,.0f} °C·min"),
        ("ISE = ∫e² dt", f"{m.ise / 60:,.0f} °C²·min"),
    ]
    if not m.hay_salto:
        filas = filas[4:]
    izquierda, derecha = st.columns((3, 2))
    izquierda.table({"Métrica": [f for f, _ in filas], "Valor": [v for _, v in filas]})
    with derecha:
        st.caption("IAE e ISE: menor es mejor, y solo se comparan corridas de la **misma duración**.")
        st.download_button("⬇ Descargar la corrida (CSV)", datos.csv(sim.historial),
                           file_name=datos.nombre_csv(sim), mime="text/csv", key="b_csv",
                           on_click="ignore", width="stretch")
        st.caption("Columnas: " + ", ".join(datos.COLUMNAS_CSV) + ". Separador «,» y punto decimal.")


# ======================================================================
def main():
    st.set_page_config(page_title="Horno virtual · PID", page_icon="🔥", layout="wide")
    ss = _estado()
    modo = _barra_lateral(ss)
    _aplicar_widgets(ss.sim)

    st.html(monitor.ESTILOS_GLOBALES)
    st.markdown(f"#### 🔥 Horno virtual · Control PID &nbsp; <small style='opacity:.6'>"
                f"{tema.INSTITUCION} · Métodos Numéricos · {tema.APP_VERSION}</small>",
                unsafe_allow_html=True)

    intervalo = 1.0 / limites.REFRESCO_HZ if ss.en_vivo else None

    @st.fragment(run_every=intervalo)
    def fragmento_monitor():
        _monitor(ss, modo)

    @st.fragment(run_every=intervalo)
    def fragmento_tablero():
        _tablero(ss, modo)

    # Pestañas normales: cambiar de pestaña no vuelve a ejecutar Python, así
    # que la corrida en vivo sigue avanzando mientras se mira la otra.
    pestana_monitor, pestana_valores = st.tabs(["📈 Monitor", "🔢 Indicadores"])
    with pestana_monitor:
        fragmento_monitor()
    with pestana_valores:
        fragmento_tablero()
        if not ss.en_vivo:
            _resultados(ss.sim)
