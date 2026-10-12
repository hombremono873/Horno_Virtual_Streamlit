"""Pruebas de humo de la página web con streamlit.testing (sin navegador ni servidor)."""
import io
from pathlib import Path

import pandas as pd
import pytest

from simulador_horno.web import datos
from simulador_horno.web import indicadores as ind

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def abrir():
    """Carga la app y pasa la portada de créditos."""
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    at.button(key="b_abrir").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_la_portada_muestra_los_creditos_y_abre_el_simulador():
    from simulador_horno import creditos
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    from simulador_horno.web import bienvenida
    portada = bienvenida._html()
    for texto in ("Omar Alberto Torres", "Yony Ceballos", "Métodos Numéricos", "Ingeniería de Sistemas",
                  "Universidad de Antioquia", "2026"):
        assert texto in portada, texto
    assert not at.sidebar.button, "la barra lateral no se dibuja en la portada"
    at.button(key="b_abrir").click().run()
    assert at.session_state.app_abierta and at.sidebar.button
    barra = " ".join(md.value for md in at.sidebar.markdown)
    assert creditos.DOCENTE in barra and creditos.AUTOR in barra   # créditos siempre visibles


def valores(at):
    """Lo que muestran los indicadores del monitor (componente del navegador)."""
    sim = at.session_state.sim
    return dict(ind.indicadores(sim, at.segmented_control(key="w_modo").value == "En vivo", sim.metricas()))


def simular(at):
    if at.segmented_control(key="w_modo").value != "Corrida completa":
        at.segmented_control(key="w_modo").set_value("Corrida completa").run()
    at.button(key="b_simular").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_la_app_carga_sin_errores():
    at = abrir()
    assert any("Horno virtual" in md.value for md in at.markdown)
    assert valores(at)["Tiempo simulado"] == "0:00:00"
    assert [t.label for t in at.tabs] == ["📈 Monitor", "🔥 Horno", "🔢 Indicadores", "⚡ Actuador", "📟 Osciloscopio"]
    assert at.segmented_control(key="w_modo").value == "En vivo"     # arranca en vivo
    assert at.selectbox(key="w_velocidad").value == "x60"
    assert at.session_state.sim.config.horno.B == pytest.approx((1300 - 30) / 3000)


def test_corrida_completa_produce_figura_y_metricas():
    at = simular(abrir())
    m = valores(at)
    assert m["Tiempo simulado"] == "2:00:00"
    assert m["Sobrepaso"] == "0.55 %" and m["Tiempo al 90 %"] == "58.2 min"
    assert at.table, "falta la tabla de desempeño"
    assert "Corrida terminada" in ind.estado(at.session_state.sim, at.session_state.en_vivo)[0]


def test_el_csv_tiene_las_columnas_esperadas():
    at = simular(abrir())
    sim = at.session_state.sim
    df = pd.read_csv(io.BytesIO(datos.csv(sim.historial)))
    assert list(df.columns) == list(datos.COLUMNAS_CSV)
    assert len(df) == len(sim.historial) == 7200
    assert at.get("download_button"), "falta el botón de descarga"


def test_los_parametros_de_la_barra_lateral_llegan_al_simulador():
    at = abrir()
    at.number_input(key="w_T_SET").set_value(800.0)
    at.selectbox(key="w_anti_windup").set_value("ninguno")
    at.selectbox(key="w_metodo").set_value("rk4")
    simular(at)
    sim = at.session_state.sim
    assert sim.config.horno.T_SET == 800.0 and sim.config.pid.anti_windup == "ninguno"
    assert sim.metodo == "rk4"
    assert sim.historial.setpoints[-1] == 800.0


def test_la_segunda_corrida_se_superpone_a_la_anterior():
    at = simular(abrir())
    assert at.session_state.anterior is None
    at.number_input(key="w_KP").set_value(50.0)
    simular(at)
    assert at.session_state.anterior is not None
    fig = at.session_state.anterior
    assert fig["etiqueta"] == "Corrida anterior" and len(fig["minutos"]) <= datos.MAX_PUNTOS + 1


def test_semilla_fija_repite_la_corrida_con_perturbaciones():
    def correr():
        at = abrir()
        at.toggle(key="w_flag_error").set_value(True)
        at.toggle(key="w_puerta").set_value(True)
        at.toggle(key="w_fijar_semilla").set_value(True)
        simular(at)
        sim = at.session_state.sim
        return sim.impulsos, sim.aperturas, sim.historial.temperaturas[-1]
    assert correr() == correr()


def test_en_vivo_avanza_y_se_pausa():
    at = abrir()
    at.segmented_control(key="w_modo").set_value("En vivo").run()
    at.selectbox(key="w_velocidad").set_value("x600").run()
    at.button(key="b_vivo").click().run()
    assert at.session_state.en_vivo
    t1 = at.session_state.sim.t
    assert t1 > 0
    at.run()                                   # otro refresco
    assert at.session_state.sim.t > t1
    at.button(key="b_vivo").click().run()      # pausar
    assert not at.session_state.en_vivo
    t2 = at.session_state.sim.t
    at.run()
    assert at.session_state.sim.t == t2        # en pausa no avanza
    at.button(key="b_reiniciar").click().run()
    assert at.session_state.sim.t == 0.0


def test_dos_sesiones_no_se_afectan():
    """Cambiar un parámetro y simular en una sesión no cambia la otra."""
    a, b = abrir(), abrir()
    a.number_input(key="w_T_SET").set_value(700.0)
    a.number_input(key="w_KP").set_value(20.0)
    simular(a)
    simular(b)
    sa, sb = a.session_state.sim, b.session_state.sim
    assert sa is not sb and sa.config is not sb.config
    assert sb.config.horno.T_SET == 1000.0 and sb.config.pid.KP == 200
    assert valores(b)["Sobrepaso"] == "0.55 %"
    assert sa.historial.setpoints[-1] == 700.0


def test_modo_manual_desde_la_barra_lateral():
    at = abrir()
    at.segmented_control(key="w_modo_control").set_value("Manual").run()
    at.slider(key="w_potencia_manual").set_value(76.4).run()
    simular(at)
    sim = at.session_state.sim
    assert sim.config.pid.modo_control == "manual"
    assert all(u == pytest.approx(0.764) for u in sim.historial.potencias)


def test_limite_de_potencia_desde_la_barra_lateral():
    at = abrir()
    at.slider(key="w_limite").set_value(60).run()
    simular(at)
    sim = at.session_state.sim
    assert max(sim.historial.potencias) == pytest.approx(0.6) and sim.T < 800


def test_triac_compensado_desde_la_barra_lateral():
    at = abrir()
    at.selectbox(key="w_actuador").set_value("triac_compensado").run()
    simular(at)
    sim = at.session_state.sim
    assert sim.config.actuador.modo == "triac_compensado"
    assert sim.alfa == pytest.approx(64.65, abs=0.3) and abs(sim.T - 1000) < 0.5
    assert at.table, "falta la tabla Newton contra bisección"


def test_osciloscopio_en_vivo_y_explorando():
    at = abrir()
    at.selectbox(key="w_actuador").set_value("triac_compensado").run()
    simular(at)
    assert not at.exception
    at.radio(key="w_osc_fuente").set_value("Explorar (ángulo a mano)").run()
    at.slider(key="w_osc_alfa").set_value(90.0).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state.w_osc_fuente == "Explorar (ángulo a mano)" and at.session_state.w_osc_alfa == 90.0
    assert at.session_state.sim.alfa == pytest.approx(64.65, abs=0.3)   # la simulación sigue en su ángulo


def test_interruptor_desde_la_barra_lateral():
    at = abrir()
    at.toggle(key="w_encendido").set_value(False).run()
    simular(at)
    sim = at.session_state.sim
    assert not sim.config.actuador.encendido and sim.energia_j == 0.0 and sim.T == pytest.approx(30.0)
