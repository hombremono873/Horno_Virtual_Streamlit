"""Piezas de la interfaz web que no necesitan Streamlit: datos, gráficas y modo en vivo."""
import io
from datetime import datetime

import pandas as pd
import pytest

from simulador_horno.configuracion.parametros import (
    Configuracion, ParametrosSimulacion, Perturbaciones,
)
from simulador_horno.simulacion.simulador import Simulador
from simulador_horno.web import datos, graficas
from simulador_horno.web.ejecucion import EjecucionEnVivo


@pytest.fixture(scope="module")
def corrida():
    sim = Simulador()
    sim.completar()          # 2 h por defecto -> 7200 muestras
    return sim


# ---- diezmado ----------------------------------------------------------
@pytest.mark.parametrize("n", [0, 1, 1999, 2000, 2001, 7200, 43200])
def test_diezmado(n):
    idx = list(datos.indices_diezmados(n))
    assert len(idx) <= datos.MAX_PUNTOS + 1
    if n:
        assert idx[0] == 0 and idx[-1] == n - 1      # arranque y última muestra siempre
        assert idx == sorted(set(idx))


# ---- CSV ---------------------------------------------------------------
def test_csv_columnas_y_formato_estandar(corrida):
    crudo = datos.csv(corrida.historial)
    texto = crudo.decode("utf-8")
    assert texto.splitlines()[0] == ",".join(datos.COLUMNAS_CSV)
    df = pd.read_csv(io.BytesIO(crudo))                  # lector estándar: "," y punto decimal
    assert list(df.columns) == list(datos.COLUMNAS_CSV)
    assert len(df) == len(corrida.historial)              # sin diezmar
    assert df["T"].iloc[-1] == pytest.approx(corrida.historial.temperaturas[-1], abs=1e-4)


def test_csv_sin_perturbaciones_la_medida_es_la_real(corrida):
    df = datos.tabla(corrida.historial)
    assert (df["perturbacion"].abs() < 1e-9).all()
    assert ((df["T_medida"] - df["T"]).abs() < 1e-9).all()


def test_csv_con_perturbaciones_de_la_medicion():
    config = Configuracion(perturbaciones=Perturbaciones(ruido_termopar=True))
    sim = Simulador(config, semilla=1)
    sim.avanzar(36_000)
    df = datos.tabla(sim.historial)
    assert df["perturbacion"].std() == pytest.approx(1.0, rel=0.15)   # σ del termopar
    assert ((df["T_medida"] - df["T"]) - (-df["perturbacion"])).abs().max() < 1e-9


def test_nombre_del_csv(corrida):
    assert datos.nombre_csv(corrida, datetime(2026, 10, 8, 14, 30, 15)) == \
        "horno_2026-10-08_143015_euler_dt0.1_condicional.csv"


# ---- gráficas ----------------------------------------------------------
def test_figura_con_subgraficas_y_pocos_puntos():
    sim = Simulador(Configuracion(simulacion=ParametrosSimulacion(duracion_horas=8)))
    sim.completar()                                       # 28 800 muestras
    fig = graficas.figura_monitor(sim.historial, sim.duracion)
    nombres = [t.name for t in fig.data]
    assert nombres == ["Setpoint", "Temperatura", "Error", "u", "Franja térmica"]
    for traza in fig.data:
        assert len(traza.x) <= datos.MAX_PUNTOS + 1
    franja = fig.data[-1]
    assert franja.type == "heatmap" and franja.colorscale[0][1] == "#0d0887"   # Plasma
    assert fig.layout.xaxis4.range == (0, 480)            # eje x en minutos, de 0 a la duración
    assert fig.layout.template.layout.paper_bgcolor.lower() == "#11111b"


def test_superponer_la_corrida_anterior(corrida):
    anterior = graficas.instantanea(corrida.historial)
    fig = graficas.figura_monitor(corrida.historial, corrida.duracion, anterior)
    assert [t.name for t in fig.data].count("Corrida anterior") == 3   # T, error y u


def test_plantilla_usa_el_tema():
    from simulador_horno.estilos import tema
    p = graficas.plantilla().layout
    assert p.plot_bgcolor.lower() == tema.G_PANEL and p.font.color.lower() == tema.G_TEXTO


# ---- modo en vivo --------------------------------------------------------
class RelojFalso:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def en_vivo(velocidad, horas=2):
    sim = Simulador(Configuracion(simulacion=ParametrosSimulacion(velocidad=velocidad, duracion_horas=horas)))
    reloj = RelojFalso()
    return sim, reloj, EjecucionEnVivo(sim, hz=4, reloj=reloj)


def test_en_vivo_respeta_el_factor_con_refrescos_irregulares():
    sim, reloj, vivo = en_vivo("x60")
    vivo.refresco()                          # primer refresco: 1/4 s -> 15 s simulados
    for dt_real in [0.25, 0.4, 0.1, 0.3] * 10:   # el navegador no refresca a ritmo fijo
        reloj.t += dt_real
        vivo.refresco()
    assert sim.t == pytest.approx(15 + 60 * 10.5, abs=0.2)


def test_en_vivo_no_recupera_una_pausa():
    sim, reloj, vivo = en_vivo("x10")
    vivo.refresco()
    vivo.pausar()
    reloj.t += 600.0                         # 10 min de pausa
    vivo.refresco()
    assert sim.t == pytest.approx(5.0, abs=0.2)    # dos refrescos de 1/4 s a x10


def test_en_vivo_se_detiene_en_la_duracion():
    sim, reloj, vivo = en_vivo("x600", horas=0.25)
    for _ in range(100):
        reloj.t += 0.25
        vivo.refresco()
    assert sim.terminada and sim.t == pytest.approx(900.0, abs=0.05)
    assert vivo.refresco() == 0


def test_en_vivo_maxima_avanza_y_termina():
    sim = Simulador(Configuracion(simulacion=ParametrosSimulacion(velocidad="máxima", duracion_horas=0.5)))
    vivo = EjecucionEnVivo(sim)              # reloj real
    while not sim.terminada:
        assert vivo.refresco() > 0
    assert sim.t == pytest.approx(1800.0, abs=0.05)


def test_impulsos_nuevos_se_avisan_una_vez():
    config = Configuracion(perturbaciones=Perturbaciones(flag_error=True, tasa_impulsos_hora=60))
    sim = Simulador(config, semilla=8)
    vivo = EjecucionEnVivo(sim)
    sim.avanzar(36_000)
    assert vivo.impulsos_nuevos() == sim.impulsos > 0
    assert vivo.impulsos_nuevos() == 0


def test_tema_de_streamlit_coherente_con_el_tema_del_simulador():
    import tomllib
    from pathlib import Path

    from simulador_horno.estilos import tema
    ruta = Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"
    t = tomllib.loads(ruta.read_text(encoding="utf-8"))["theme"]
    assert (t["backgroundColor"], t["secondaryBackgroundColor"], t["textColor"]) == \
        (tema.G_FONDO, tema.G_PANEL, tema.G_TEXTO)
