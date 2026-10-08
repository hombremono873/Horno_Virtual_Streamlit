"""Anti-windup: ninguno, recorte (original) e integración condicional."""
import pytest

from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.control.anti_windup import NOMBRES, limitar
from simulador_horno.simulacion.motor import Motor

HORAS = 6


def corrida(modo, KP=200, KI=10, KD=2):
    """(sobrepaso %, error final °C, |integral| máxima) tras HORAS simuladas."""
    vpid.anti_windup, vpid.KP, vpid.KI, vpid.KD = modo, KP, KI, KD
    motor = Motor()
    T_max, I_max = motor.T, 0.0
    for _ in range(int(HORAS * 3600 / vhorno.DT)):
        motor.paso()
        T_max = max(T_max, motor.T)
        I_max = max(I_max, abs(vpid.integral))
    salto = vhorno.T_SET - vhorno.T_AMB
    return (T_max - vhorno.T_SET) / salto * 100, vhorno.T_SET - motor.T, I_max


def test_condicional_por_defecto():
    assert vpid.anti_windup == "condicional"
    assert set(NOMBRES) == {"ninguno", "recorte", "condicional"}


def test_sin_anti_windup_hay_windup():
    sobrepaso, _, I_max = corrida("ninguno")
    assert sobrepaso > 20          # el horno se pasa ~280 °C
    assert I_max > 1e6             # la integral se infla durante la subida


@pytest.mark.parametrize("KP, KI, KD", [(200, 10, 2), (200, 5, 2), (50, 2, 0)])
def test_condicional_llega_al_setpoint_con_cualquier_sintonia(KP, KI, KD):
    sobrepaso, error_final, _ = corrida("condicional", KP, KI, KD)
    assert sobrepaso < 5
    assert abs(error_final) < 0.5


def test_recorte_funciona_con_las_ganancias_por_defecto():
    sobrepaso, error_final, _ = corrida("recorte")
    assert sobrepaso < 5 and abs(error_final) < 0.5


@pytest.mark.parametrize("KP, KI, KD", [(200, 5, 2), (50, 2, 0)])
def test_recorte_deja_error_permanente_con_ki_bajo(KP, KI, KD):
    """Limitación documentada del método original: el tope fijo de la
    integral impide aportar la potencia que el equilibrio necesita."""
    _, error_final, _ = corrida("recorte", KP, KI, KD)
    assert error_final > 10


@pytest.mark.parametrize("u_bruta, error, se_congela", [
    (1.5, 100.0, True),     # saturado arriba y el error pide más: no integra
    (1.5, -5.0, False),     # saturado arriba pero el error ya pide bajar: integra
    (-0.3, -50.0, True),    # saturado abajo y el error pide menos: no integra
    (0.5, 100.0, False),    # sin saturar: integra
])
def test_regla_de_la_integracion_condicional(u_bruta, error, se_congela):
    resultado = limitar("condicional", integral_previa=10.0, integral_nueva=11.0,
                        error=error, u_bruta=u_bruta)
    assert resultado == (10.0 if se_congela else 11.0)


def test_modo_desconocido():
    with pytest.raises(ValueError):
        limitar("magico", 0.0, 1.0, 1.0, 0.5)
