"""La lógica de simulación no depende de ninguna interfaz.

El núcleo (modelo, control, numérico y simulación) debe poder importarse y
probarse sin Streamlit ni Plotly: la interfaz web es solo una capa encima.
"""
import subprocess
import sys

INTERFACES = ("streamlit", "plotly", "pandas", "rich", "PySide6", "pyqtgraph")


def test_el_nucleo_no_importa_ninguna_interfaz():
    codigo = (
        "import sys\n"
        "import simulador_horno.control.senal_error, simulador_horno.control.pid\n"
        "import simulador_horno.modelo.horno, simulador_horno.numerico.estabilidad\n"
        "import simulador_horno.simulacion.motor, simulador_horno.simulacion.reloj\n"
        "import simulador_horno.simulacion.metricas, simulador_horno.simulacion.resultados\n"
        f"malos = [m for m in {INTERFACES!r} if m in sys.modules]\n"
        "assert not malos, malos\n"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr


def test_el_motor_cuenta_los_impulsos():
    from simulador_horno.configuracion import parametros_horno as vhorno
    from simulador_horno.simulacion.motor import Motor
    vhorno.flag_error = True
    motor = Motor(semilla=11)
    motor.avanzar(int(3 * 3600 / vhorno.DT))
    assert 5 <= motor.impulsos <= 40      # ~6 por hora (tasa por defecto)
