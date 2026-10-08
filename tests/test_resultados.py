"""Guardado de las corridas en CSV (simulacion.resultados)."""
from datetime import datetime

import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.simulacion import resultados
from simulador_horno.simulacion.metricas import calcular
from simulador_horno.simulacion.motor import Motor

FECHA = datetime(2026, 10, 8, 14, 30, 15)
PARAMETROS = {"metodo": "rk4", "dt": 0.1, "anti_windup": "condicional", "KP": 200, "B": 0.42333}


@pytest.fixture
def corrida():
    motor = Motor()
    motor.avanzar(int(600 / vhorno.DT))      # 10 min simulados -> ~600 muestras
    return motor


def test_nombre_del_archivo():
    assert resultados.nombre_archivo(FECHA, "rk4", 0.1, "condicional") == \
        "2026-10-08_143015_rk4_dt0,1_condicional.csv"


def test_ida_y_vuelta(corrida, tmp_path):
    h = corrida.historial
    m = calcular(h.tiempos, h.temperaturas, vhorno.T_SET)
    ruta = resultados.guardar(h, vhorno.T_SET, PARAMETROS, m, carpeta=tmp_path, fecha=FECHA)
    assert ruta.parent == tmp_path and ruta.exists()

    parametros, series = resultados.leer(ruta)
    assert list(series) == list(resultados.COLUMNAS)
    assert len(series["t_s"]) == len(h.tiempos)
    assert series["T_C"] == pytest.approx(h.temperaturas, abs=1e-4)
    assert series["u"] == pytest.approx(h.potencias, abs=1e-5)
    assert set(series["T_set_C"]) == {vhorno.T_SET}
    assert parametros["metodo"] == "rk4" and parametros["KP"] == "200"
    assert parametros["fecha"] == "2026-10-08 14:30:15"
    assert "metrica_sobrepaso_pct" in parametros


def test_formato_para_excel_en_espanol(corrida, tmp_path):
    ruta = resultados.guardar(corrida.historial, vhorno.T_SET, PARAMETROS, carpeta=tmp_path, fecha=FECHA)
    crudo = ruta.read_bytes()
    assert crudo.startswith(b"\xef\xbb\xbf")                 # BOM: Excel muestra bien ° y tildes
    texto = crudo.decode("utf-8-sig")
    assert "t_s;T_C;T_set_C;error_C;u" in texto
    assert "# B;0,42333" in texto                             # coma decimal
    lineas = texto.splitlines()            # en Windows el archivo usa \r\n
    primera_fila = lineas[lineas.index("t_s;T_C;T_set_C;error_C;u") + 1]
    assert primera_fila.count(";") == 4 and "." not in primera_fila


def test_el_historial_registra_la_potencia(corrida):
    h = corrida.historial
    assert len(h.potencias) == len(h.tiempos)
    assert all(0.0 <= u <= 1.0 for u in h.potencias)
    assert h.potencias[0] == 1.0          # al arrancar frío va a potencia plena


def test_simulador_guarda_y_avisa_si_falla(monkeypatch, tmp_path):
    from simulador_horno.simulacion.simulador import Simulador
    sim = Simulador()
    sim.motor.avanzar(3000)
    monkeypatch.setattr(resultados, "carpeta_resultados", lambda: tmp_path)
    ruta = sim._guardar_resultados()
    assert ruta is not None and ruta.parent == tmp_path

    # carpeta imposible (es un archivo): no debe romper el simulador
    archivo = tmp_path / "no_es_carpeta"
    archivo.write_text("x")
    monkeypatch.setattr(resultados, "carpeta_resultados", lambda: archivo / "sub")
    assert sim._guardar_resultados() is None


def test_corrida_vacia_no_se_guarda():
    from simulador_horno.simulacion.simulador import Simulador
    assert Simulador()._guardar_resultados() is None
