"""Señal de control acotada a [0, 1] y desempeño de la corrida por defecto."""
import pytest

from simulador_horno.configuracion.parametros import Configuracion, Perturbaciones
from simulador_horno.control.escalado import escalar_u
from simulador_horno.simulacion.simulador import Simulador

HORAS = 4


@pytest.mark.parametrize("u_bruto, esperado", [(-1e9, 0.0), (-5.0, 0.0), (0.0, 0.0), (10000.0, 0.5), (1e9, 1.0)])
def test_escalar_u_satura_en_0_1(u_bruto, esperado):
    assert escalar_u(u_bruto) == pytest.approx(esperado)


@pytest.mark.parametrize("perturbaciones", [False, True])
def test_u_nunca_sale_de_0_1(perturbaciones):
    config = Configuracion(perturbaciones=Perturbaciones(error_oscilante=perturbaciones,
                                                         flag_error=perturbaciones))
    sim = Simulador(config, semilla=1234)
    u_min, u_max = 1.0, 0.0
    for _ in range(int(HORAS * 3600 / config.horno.DT)):
        u, _ = sim.paso()
        u_min, u_max = min(u_min, u), max(u_max, u)
    assert 0.0 <= u_min and u_max <= 1.0


def metricas_corrida_por_defecto():
    """Corre 4 h simuladas: (t al 90 %, sobrepaso %, error final °C, establecimiento ±1 %)."""
    sim = Simulador()
    horno = sim.config.horno
    salto = horno.T_SET - horno.T_AMB
    umbral_90 = horno.T_AMB + 0.9 * salto
    banda = 0.01 * salto
    t90 = t_est = None
    T_max = sim.T
    for _ in range(int(HORAS * 3600 / horno.DT)):
        sim.paso()
        T_max = max(T_max, sim.T)
        if t90 is None and sim.T >= umbral_90:
            t90 = sim.t
        if abs(horno.T_SET - sim.T) > banda:
            t_est = None
        elif t_est is None:
            t_est = sim.t
    sobrepaso = max(0.0, (T_max - horno.T_SET) / salto * 100)
    return t90, sobrepaso, horno.T_SET - sim.T, t_est


def test_corrida_por_defecto_alcanza_setpoint():
    t90, sobrepaso, error_final, t_est = metricas_corrida_por_defecto()
    print(
        f"\n  Corrida por defecto ({HORAS} h simuladas):"
        f"\n    tiempo al 90 %      : {t90 / 60:.1f} min"
        f"\n    sobrepaso           : {sobrepaso:.2f} %"
        f"\n    establecimiento ±1 %: {t_est / 60:.1f} min"
        f"\n    error final         : {error_final:+.4f} °C"
    )
    assert t90 is not None
    assert sobrepaso < 5.0
    assert t_est is not None          # entra y se queda en la banda de ±1 %
    assert abs(error_final) < 0.5
