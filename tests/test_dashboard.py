"""Dashboard de comparación de corridas guardadas."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from rich.console import Console  # noqa: E402

from simulador_horno.configuracion import parametros_horno as vhorno  # noqa: E402
from simulador_horno.configuracion import parametros_pid as vpid  # noqa: E402
from simulador_horno.interfaz.consola.dashboard import nota_comparacion, tabla_comparativa  # noqa: E402
from simulador_horno.simulacion import resultados  # noqa: E402
from simulador_horno.simulacion.metricas import calcular  # noqa: E402
from simulador_horno.simulacion.motor import Motor  # noqa: E402


def guardar_corrida(carpeta, minutos, minuto, **parametros):
    motor = Motor()
    motor.avanzar(int(minutos * 60 / vhorno.DT))
    h = motor.historial
    m = calcular(h.tiempos, h.temperaturas, vhorno.T_SET)
    datos = {"metodo": "euler", "dt": 0.1, "anti_windup": vpid.anti_windup, "KP": 200, "KI": 10, "KD": 2,
             **parametros}
    ruta = resultados.guardar(h, vhorno.T_SET, datos, m, carpeta=carpeta,
                              fecha=datetime(2026, 10, 8, 15, 0) + timedelta(minutes=minuto))
    time.sleep(0.02)   # mtime distinto para ordenar
    return ruta


@pytest.fixture
def dos_corridas(tmp_path):
    a = guardar_corrida(tmp_path, 90, 0)
    vpid.anti_windup = "ninguno"
    b = guardar_corrida(tmp_path, 90, 1, anti_windup="ninguno")
    return tmp_path, a, b


def texto(renderizable):
    c = Console(width=140, color_system=None, record=True)
    c.print(renderizable)
    return c.export_text()


def test_listar_del_mas_reciente_al_mas_antiguo(dos_corridas):
    carpeta, a, b = dos_corridas
    assert resultados.listar(carpeta) == [b, a]
    assert resultados.listar(carpeta, maximo=1) == [b]
    assert resultados.listar(carpeta / "no_existe") == []


def test_numero_y_metricas_guardadas(dos_corridas):
    assert resultados.numero("0,54") == pytest.approx(0.54)
    assert resultados.numero("") is None and resultados.numero(None) is None
    _, a, _ = dos_corridas
    metricas = resultados.metricas_guardadas(resultados.leer(a)[0])
    assert metricas["sobrepaso_pct"] == pytest.approx(0.54, abs=0.05)


def test_tabla_comparativa(dos_corridas):
    carpeta, a, b = dos_corridas
    corridas = [(r, resultados.leer(r)[0]) for r in (a, b)]
    salida = texto(tabla_comparativa(corridas))
    for esperado in ("A", "B", "condicional", "ninguno", "Sobrepaso", "IAE"):
        assert esperado in salida
    assert "comparables" not in texto(nota_comparacion(corridas))   # misma duración


def test_avisa_si_las_duraciones_difieren(tmp_path):
    a = guardar_corrida(tmp_path, 30, 0)
    b = guardar_corrida(tmp_path, 60, 1)
    corridas = [(r, resultados.leer(r)[0]) for r in (a, b)]
    assert "no son comparables" in texto(nota_comparacion(corridas))


def test_ventana_dibuja_una_curva_por_corrida(dos_corridas):
    from simulador_horno.interfaz.graficas.dashboard import VentanaDashboard
    _, a, b = dos_corridas
    v = VentanaDashboard([resultados.leer(r) for r in (a, b)])
    try:
        for grafica in (v.p_temp, v.p_err, v.p_u):
            assert len(grafica.listDataItems()) == 2
    finally:
        v.win.close()
