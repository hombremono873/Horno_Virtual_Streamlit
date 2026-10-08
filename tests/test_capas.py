"""La lógica de simulación funciona sin consola (rich) ni ventana (Qt)."""
import subprocess
import sys


def test_motor_no_importa_rich_ni_qt():
    codigo = (
        "import sys; import simulador_horno.simulacion.motor, simulador_horno.simulacion.reloj, simulador_horno.simulacion.metricas, simulador_horno.simulacion.resultados; "
        "malos = [m for m in ('rich', 'PySide6', 'pyqtgraph') if m in sys.modules]; "
        "assert not malos, malos"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr


def test_la_logica_no_importa_la_interfaz():
    """Control, modelo, numérico y motor no deben depender de la interfaz
    (antes senal_error.py disparaba la alarma sonora)."""
    codigo = (
        "import sys\n"
        "import simulador_horno.control.senal_error, simulador_horno.control.pid\n"
        "import simulador_horno.modelo.horno, simulador_horno.numerico.estabilidad\n"
        "import simulador_horno.simulacion.motor\n"
        "malos = [m for m in sys.modules if m.startswith('simulador_horno.interfaz')]\n"
        "assert not malos, malos\n"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr


def test_el_motor_cuenta_los_impulsos():
    import random
    from simulador_horno.configuracion import parametros_horno as vhorno
    from simulador_horno.simulacion.motor import Motor
    random.seed(11)
    vhorno.flag_error = True
    motor = Motor()
    motor.avanzar(int(3 * 3600 / vhorno.DT))
    assert 5 <= motor.impulsos <= 40      # ~6 por hora (tasa por defecto)
