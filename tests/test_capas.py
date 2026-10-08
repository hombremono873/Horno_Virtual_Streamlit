"""La lógica de simulación no depende de ninguna interfaz.

El núcleo (modelo, control, numérico y simulación) debe poder importarse y
probarse sin Streamlit ni Plotly: la interfaz web es solo una capa encima.
"""
import subprocess
import sys

from simulador_horno.configuracion.parametros import Configuracion, Perturbaciones
from simulador_horno.simulacion.simulador import Simulador

INTERFACES = ("streamlit", "plotly", "pandas", "rich", "PySide6", "pyqtgraph")


def test_el_nucleo_no_importa_ninguna_interfaz():
    codigo = (
        "import sys\n"
        "import simulador_horno.control.senal_error, simulador_horno.control.pid\n"
        "import simulador_horno.modelo.horno, simulador_horno.numerico.estabilidad\n"
        "import simulador_horno.simulacion.simulador, simulador_horno.simulacion.reloj\n"
        "import simulador_horno.simulacion.metricas, simulador_horno.simulacion.resultados\n"
        f"malos = [m for m in {INTERFACES!r} if m in sys.modules]\n"
        "malos += [m for m in sys.modules if m.startswith('simulador_horno.web')]\n"
        "assert not malos, malos\n"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr


def test_el_simulador_cuenta_los_impulsos():
    sim = Simulador(Configuracion(perturbaciones=Perturbaciones(flag_error=True)), semilla=11)
    sim.avanzar(int(3 * 3600 / sim.config.horno.DT))
    assert 5 <= sim.impulsos <= 40      # ~6 por hora (tasa por defecto)
