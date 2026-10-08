"""Lectura de las corridas guardadas: la base del dashboard de comparación."""
import time
from datetime import datetime, timedelta

import pytest

from simulador_horno.configuracion.parametros import Configuracion, ParametrosPID
from simulador_horno.simulacion import resultados
from simulador_horno.simulacion.simulador import Simulador


def guardar_corrida(carpeta, minutos, minuto, anti_windup="condicional"):
    sim = Simulador(Configuracion(pid=ParametrosPID(anti_windup=anti_windup)))
    sim.avanzar(int(minutos * 60 / sim.config.horno.DT))
    ruta = resultados.guardar(sim.historial, sim.config.horno.T_SET, sim.parametros_corrida(),
                              sim.metricas(), carpeta=carpeta,
                              fecha=datetime(2026, 10, 8, 15, 0) + timedelta(minutes=minuto))
    time.sleep(0.02)   # mtime distinto para ordenar
    return ruta


@pytest.fixture
def dos_corridas(tmp_path):
    a = guardar_corrida(tmp_path, 90, 0)
    b = guardar_corrida(tmp_path, 90, 1, anti_windup="ninguno")
    return tmp_path, a, b


def test_listar_del_mas_reciente_al_mas_antiguo(dos_corridas):
    carpeta, a, b = dos_corridas
    assert resultados.listar(carpeta) == [b, a]
    assert resultados.listar(carpeta, maximo=1) == [b]
    assert resultados.listar(carpeta / "no_existe") == []


def test_numero_y_metricas_guardadas(dos_corridas):
    assert resultados.numero("0,54") == pytest.approx(0.54)
    assert resultados.numero("") is None and resultados.numero(None) is None
    _, a, b = dos_corridas
    metricas = resultados.metricas_guardadas(resultados.leer(a)[0])
    assert metricas["sobrepaso_pct"] == pytest.approx(0.54, abs=0.05)
    assert resultados.leer(b)[0]["anti_windup"] == "ninguno"
