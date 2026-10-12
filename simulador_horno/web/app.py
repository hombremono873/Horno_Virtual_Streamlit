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
from simulador_horno import creditos
from simulador_horno.modelo import triac
from simulador_horno.web import bienvenida, datos, graficas, monitor
from simulador_horno.web import indicadores as ind
from simulador_horno.web.ejecucion import EjecucionEnVivo

DEFECTO = Configuracion()
MODOS = ("Corrida completa", "En vivo")
CONTROLES = ("Automático", "Manual")
MANUAL_POR = ("Potencia (%)", "Ángulo α (°)")
FUENTES_OSCILOSCOPIO = ("En vivo (simulación)", "Explorar (ángulo a mano)")
REFRESCO_OSCILOSCOPIO = 1.0   # s
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
    # control y actuador (algunos widgets solo existen en un modo: se leen con valor por defecto)
    c.pid.modo_control = "manual" if ss.get("w_modo_control") == "Manual" else "automatico"
    c.pid.limite_potencia = ss.get("w_limite", 100) / 100
    c.pid.potencia_manual = _potencia_manual(ss)
    a = c.actuador
    a.encendido = bool(ss.get("w_encendido", True))
    a.modo = ss.get("w_actuador", DEFECTO.actuador.modo)
    a.metodo = ss.get("w_metodo_inversion", DEFECTO.actuador.metodo)
    a.V_red = float(ss.get("w_V_red", DEFECTO.actuador.V_red))
    a.potencia_nominal = float(ss.get("w_P_nominal", DEFECTO.actuador.potencia_nominal))
    a.resolucion = float(ss.get("w_resolucion", DEFECTO.actuador.resolucion))
    a.dispersion = float(ss.get("w_dispersion", DEFECTO.actuador.dispersion))


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


def _abrir_simulador():
    st.session_state.app_abierta = True


@st.dialog("Créditos", width="large")
def _ver_creditos():
    bienvenida.creditos_en_ventana()


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


def _control_y_actuador():
    """Automático (PID, con límite de potencia) o manual (el usuario fija la potencia), y el triac."""
    ss = st.session_state
    a = DEFECTO.actuador
    control = st.segmented_control("Control", CONTROLES, default=CONTROLES[0], required=True,
                                   key="w_modo_control", width="stretch",
                                   help="Automático: el PID decide la potencia. Manual: la decides tú "
                                        "(lazo abierto: nadie corrige las perturbaciones).")
    if control == "Automático":
        st.slider("Límite de potencia (%)", 10, 100, 100, 1, key="w_limite",
                  help="Máxima potencia que el PID puede usar. Con poco límite el horno no llega al setpoint.")
    else:
        por = st.radio("Fijar la potencia por", MANUAL_POR, horizontal=True, key="w_manual_por")
        if por == MANUAL_POR[0]:
            pct = st.slider("Potencia (%)", 0.0, 100.0, 50.0, 0.1, key="w_potencia_manual")
            if 0 < pct < 100:
                alfa, _ = triac.angulo_compensado(pct / 100)
                st.caption(f"Equivale a un ángulo de disparo α = **{alfa:.2f}°**.")
        else:
            alfa = st.slider("Ángulo de disparo α (°)", a.alfa_min, a.alfa_max, 90.0, 0.05, key="w_alfa_manual")
            st.caption(f"Entrega el **{triac.fraccion_potencia(alfa) * 100:.2f} %** de la potencia.")
        st.caption(f"Temperatura final sin perturbaciones ≈ "
                   f"**{_temperatura_final(ss):.0f} °C** (ambiente + potencia × (T_MAX_EQ − ambiente)).")
    st.selectbox("Actuador", list(triac.MODOS), format_func=triac.MODOS.get,
                 index=list(triac.MODOS).index(a.modo), key="w_actuador",
                 help="Ideal: llega exactamente la potencia pedida. Triac lineal: α = 180·(1 − u), entrega "
                      "otra potencia. Triac compensado: invierte la curva con un método numérico.")
    st.selectbox("Método para invertir la curva", list(triac.METODOS_INVERSION),
                 format_func=triac.METODOS_INVERSION.get, key="w_metodo_inversion",
                 disabled=ss.get("w_actuador", a.modo) != "triac_compensado")
    c1, c2 = st.columns(2)
    c1.selectbox("Red (VCA)", (220.0, 110.0), index=0, key="w_V_red")
    c2.number_input("Potencia (W)", 200.0, 50000.0, a.potencia_nominal, 100.0, key="w_P_nominal")
    c1.number_input("Resolución (°)", 0.0, 10.0, a.resolucion, 0.5, key="w_resolucion",
                    help="Paso del temporizador de disparo. 0 = continuo.")
    c2.number_input("Dispersión (°)", 0.0, 10.0, a.dispersion, 0.1, key="w_dispersion",
                    help="Desviación típica del instante de disparo (usa la semilla de la corrida).")


def _potencia_manual(ss):
    if ss.get("w_manual_por", MANUAL_POR[0]) == MANUAL_POR[1]:
        return triac.fraccion_potencia(ss.get("w_alfa_manual", 90.0))
    return ss.get("w_potencia_manual", 50.0) / 100


def _temperatura_final(ss):
    """Equilibrio en lazo abierto: T_AMB + potencia·(T_MAX_EQ − T_AMB)."""
    T_amb, T_max = ss.get("w_T_AMB", DEFECTO.horno.T_AMB), ss.get("w_T_MAX_EQ", DEFECTO.horno.T_MAX_EQ)
    return T_amb + _potencia_manual(ss) * (T_max - T_amb)


def _barra_lateral(ss):
    sim = ss.sim
    with st.sidebar:
        st.markdown(f"**{tema.APP_NOMBRE}**  \n{creditos.UNIVERSIDAD} · {creditos.ASIGNATURA}  \n"
                    f"Autor: **{creditos.AUTOR}** · Docente: **{creditos.DOCENTE}**")
        modo = st.segmented_control("Modo", MODOS, default=MODOS[1], required=True,
                                    key="w_modo", on_change=_cambio_de_modo, width="stretch")
        st.toggle("⏻ Horno encendido (interruptor de potencia)", True, key="w_encendido",
                  help="Apagado corta la energía a la resistencia. El control sigue midiendo y calculando "
                       "(como en un horno real): el termopar, el PID y los pulsos del triac continúan.")

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

        with st.expander("Control y actuador (triac)", expanded=True):
            _control_y_actuador()

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
        if st.button("ℹ Créditos", width="stretch", key="b_creditos"):
            _ver_creditos()
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
        mostrar_entregada=sim.config.actuador.modo != "ideal",
    )
    monitor.lienzo(figura, [f"⏱ {ind.hhmmss(sim.t)}"] + ind.estado(sim, ss.en_vivo))
    if ss.en_vivo and sim.terminada:
        ss.en_vivo = False
        st.rerun()   # detiene el refresco automático y actualiza los botones


def _actuador(ss):
    """La curva del triac con el punto de trabajo actual (se actualiza en vivo)."""
    monitor.grafica(graficas.figura_actuador(ss.sim), key="grafica_triac")


def _controles_osciloscopio():
    c1, c2 = st.columns((1, 2))
    fuente = c1.radio("Ángulo que se muestra", FUENTES_OSCILOSCOPIO, key="w_osc_fuente",
                      help="En vivo: el ángulo con que el triac está disparando en la simulación. "
                           "Explorar: mueve tú el ángulo de disparo.")
    c2.slider("Ángulo de disparo para explorar (°)", 0.0, 180.0, 64.65, 0.05, key="w_osc_alfa",
              disabled=fuente != FUENTES_OSCILOSCOPIO[1],
              help="Por debajo del mínimo el triac conduce el ciclo completo; por encima del máximo no conduce.")


def _angulo_osciloscopio(ss):
    """(ángulo de disparo, aviso): el de la simulación en vivo o el que se explora a mano."""
    sim, act = ss.sim, ss.sim.config.actuador
    if st.session_state.get("w_osc_fuente", FUENTES_OSCILOSCOPIO[0]) == FUENTES_OSCILOSCOPIO[1]:
        pedido = st.session_state.get("w_osc_alfa", 64.65)
        return triac.disparo_real(pedido, act.alfa_min, act.alfa_max), f"Explorando: ángulo pedido {pedido:.2f}°"
    if act.modo == "ideal":
        alfa, _ = triac.angulo_compensado(sim.u) if 0 < sim.u < 1 else (180.0 if sim.u <= 0 else 0.0, 0)
        alfa = triac.disparo_real(alfa, act.alfa_min, act.alfa_max)
        return alfa, "Actuador ideal (sin triac): se muestra el ángulo equivalente"
    alfa = triac.ALFA_APAGADO if sim.alfa != sim.alfa else sim.alfa   # NaN (aún sin pasos) = apagado
    return alfa, f"En vivo · {triac.MODOS[act.modo]}"


def _osciloscopio(ss):
    act = ss.sim.config.actuador
    alfa, aviso = _angulo_osciloscopio(ss)
    ondas = triac.formas_de_onda(alfa, act.V_red, act.R, act.frecuencia, resolucion=0.5, encendido=act.encendido)
    m = triac.medidas(ondas)
    formula = triac.potencia_electrica(alfa, act.V_red, act.R) if act.encendido else 0.0
    if alfa <= 0:
        disparo = "compuerta activa todo el ciclo: conducción completa"
    elif alfa >= triac.ALFA_APAGADO:
        disparo = "sin disparo: el triac no conduce"
    else:
        disparo = f"disparo α = <b>{alfa:.2f}°</b>, a {triac.tiempo_disparo_ms(alfa, act.frecuencia):.3f} ms del cruce por cero"
    if not act.encendido:
        aviso = '<b class="alerta">⏻ HORNO APAGADO: hay red y pulsos, pero no llega energía</b> · ' + aviso
    estado = [aviso, disparo,
              f"V eficaz en la carga {m['V_rms_carga']:.1f} V",
              f"I eficaz {m['I_rms']:.2f} A",
              f"P media integrando la onda <b>{m['P_media']:,.1f} W</b> · fórmula {formula:,.1f} W"]
    monitor.grafica(graficas.figura_osciloscopio(ondas, alfa, act.frecuencia), key="osciloscopio", estado=estado)


def _explicacion_osciloscopio():
    st.markdown(
        "**Cómo leerlo.** En cada medio ciclo el circuito detecta el **cruce por cero** de la red (líneas punteadas), "
        "espera el tiempo que corresponde al ángulo α y envía un **pulso corto a la compuerta** (CH5). El triac se "
        "enciende y sigue conduciendo solo hasta el siguiente cruce por cero: por eso la onda en la resistencia "
        "(CH2) aparece **recortada**. La corriente (CH3) tiene la misma forma porque la carga es una resistencia, "
        "y la potencia instantánea (CH4) es voltaje × corriente: siempre positiva. Mientras el triac no conduce, "
        "todo el voltaje de la red queda sobre él (línea gris).\n\n"
        "Pasa el mouse sobre la pantalla para leer todos los canales en ese instante; haz clic en un canal de la "
        "leyenda para apagarlo o encenderlo. La **potencia media** se calcula integrando la onda (regla del "
        "trapecio) y coincide con la fórmula del triac."
    )


def _explicacion_triac():
    """Texto y tabla fija: cómo funciona el triac y cómo se invierte su curva."""
    st.markdown(
        "El **triac** recorta cada medio ciclo de la red: espera un **ángulo de disparo α** y conduce "
        "desde ahí. La potencia que entrega **no es proporcional** al ángulo:\n\n"
        "`fracción de potencia = 1 − α/180 + sen(2α) / (2 × 3,1416)`\n\n"
        "Si se usa el ángulo lineal α = 180 × (1 − u), el horno recibe otra potencia que la pedida "
        "(con u = 76,4 % llega el 92,3 %). Para entregar exactamente u hay que **invertir la curva**: "
        "hallar α tal que fracción(α) = u. La ecuación no se despeja; se resuelve con **bisección** o "
        "**Newton-Raphson**.\n\n"
        f"**Zonas grises:** en los extremos el triac no puede regular. Si el ángulo pedido es menor que "
        f"{DEFECTO.actuador.alfa_min:g}° apenas hay voltaje para cebarlo, y el circuito deja la compuerta "
        "activa todo el ciclo: **conducción completa (100 %)**. Si es mayor que "
        f"{DEFECTO.actuador.alfa_max:g}° el medio ciclo se está acabando, la corriente no alcanza la de "
        "mantenimiento y el triac **no conduce (0 %)**."
    )
    filas = []
    for u in (0.001, 0.05, 0.25, 0.5, 0.764, 0.9, 0.99, 0.999):
        a_n, it_n = triac.angulo_por_newton(u)
        a_b, it_b = triac.angulo_por_biseccion(u)
        filas.append({"Potencia pedida": f"{u * 100:g} %", "Ángulo α": f"{a_n:.4f}°",
                      "Iteraciones Newton": it_n, "Iteraciones bisección": it_b,
                      "Ángulo lineal entregaría": f"{triac.fraccion_potencia(triac.angulo_lineal(u)) * 100:.1f} %"})
    st.caption("Newton-Raphson contra bisección (tolerancia 1e-9 grados):")
    st.table(filas)


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
    if not ss.get("app_abierta"):   # al iniciar: portada con los créditos
        bienvenida.mostrar(_abrir_simulador)
        return
    modo = _barra_lateral(ss)
    _aplicar_widgets(ss.sim)

    st.html(monitor.ESTILOS_GLOBALES)
    st.markdown(f"#### 🔥 Horno virtual · Control PID &nbsp; <small style='opacity:.6'>"
                f"{creditos.UNIVERSIDAD} · {creditos.ASIGNATURA} · {creditos.AUTOR} · "
                f"Docente {creditos.DOCENTE} · {tema.APP_VERSION}</small>",
                unsafe_allow_html=True)

    intervalo = 1.0 / limites.REFRESCO_HZ if ss.en_vivo else None

    @st.fragment(run_every=intervalo)
    def fragmento_monitor():
        _monitor(ss, modo)

    @st.fragment(run_every=intervalo)
    def fragmento_tablero():
        _tablero(ss, modo)

    @st.fragment(run_every=intervalo)
    def fragmento_actuador():
        _actuador(ss)

    # el osciloscopio pesa más (miles de puntos) y el ángulo cambia despacio: 1 vez por segundo
    @st.fragment(run_every=REFRESCO_OSCILOSCOPIO if ss.en_vivo else None)
    def fragmento_osciloscopio():
        _osciloscopio(ss)

    # Pestañas normales: cambiar de pestaña no vuelve a ejecutar Python, así
    # que la corrida en vivo sigue avanzando mientras se mira la otra.
    pestana_monitor, pestana_valores, pestana_triac, pestana_osc = st.tabs(
        ["📈 Monitor", "🔢 Indicadores", "⚡ Actuador", "📟 Osciloscopio"])
    with pestana_monitor:
        fragmento_monitor()
    with pestana_valores:
        fragmento_tablero()
        if not ss.en_vivo:
            _resultados(ss.sim)
    with pestana_triac:
        fragmento_actuador()
        _explicacion_triac()
    with pestana_osc:
        _controles_osciloscopio()
        fragmento_osciloscopio()
        _explicacion_osciloscopio()
