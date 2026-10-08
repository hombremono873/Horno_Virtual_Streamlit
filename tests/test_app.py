"""Pruebas de humo de la página web con streamlit.testing (sin navegador ni servidor)."""
import io
from pathlib import Path

import pandas as pd
import pytest

from simulador_horno.web import datos

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def abrir():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def metricas(at):
    return {m.label: m.value for m in at.metric}


def simular(at):
    at.button(key="b_simular").click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_la_app_carga_sin_errores():
    at = abrir()
    assert at.title[0].value.startswith("🔥 Horno virtual")
    assert metricas(at)["Tiempo simulado"] == "0:00:00"
    assert at.session_state.sim.config.horno.B == pytest.approx((1300 - 30) / 3000)


def test_corrida_completa_produce_figura_y_metricas():
    at = simular(abrir())
    m = metricas(at)
    assert m["Tiempo simulado"] == "2:00:00"
    assert m["Sobrepaso"] == "0.54 %" and m["Tiempo al 90 %"] == "58.2 min"
    assert len(at.get("plotly_chart")) == 1
    assert at.table, "falta la tabla de desempeño"
    assert any("Corrida terminada" in md.value for md in at.markdown)


def test_el_csv_tiene_las_columnas_esperadas():
    at = simular(abrir())
    sim = at.session_state.sim
    df = pd.read_csv(io.BytesIO(datos.csv(sim.historial)))
    assert list(df.columns) == ["t_s", "T", "T_set", "error", "u", "P", "I", "D", "perturbacion", "T_medida"]
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
    assert metricas(b)["Sobrepaso"] == "0.54 %"
    assert sa.historial.setpoints[-1] == 700.0
