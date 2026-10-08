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
