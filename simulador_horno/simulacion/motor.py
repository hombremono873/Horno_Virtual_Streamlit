"""Motor de la simulación: la lógica de cada paso, sin consola ni ventana.

Separado de ``Simulador`` (que pinta) para poder probarlo con pytest en
un entorno sin pantalla y para que la velocidad de ejecución no altere
los resultados: el motor solo sabe de pasos de ``DT`` simulado.
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.configuracion import parametros_simulacion as vsim
from simulador_horno.control.pid import actualizar_pid
from simulador_horno.control.senal_error import construir_error
from simulador_horno.modelo.perturbaciones import reiniciar_impulso
from simulador_horno.numerico.integradores import METODOS
from simulador_horno.simulacion.historial import Historial


class Motor:
    """Estado de una corrida: temperatura, tiempo simulado e historial."""

    def __init__(self, max_muestras=limites.MAX_MUESTRAS, intervalo=limites.INTERVALO_MUESTREO):
        self._reiniciar_estado()
        vhorno.recalcular_B()
        self.metodo = vsim.metodo
        self._integrar = METODOS[self.metodo]   # Euler, Heun o RK4, fijo durante la corrida
        self.T = vhorno.T_INICIAL   # T_AMB = arranque en frío; mayor = en caliente
        self.t = 0.0
        self.u = 0.0
        self.error = vhorno.T_SET - self.T
        self.historial = Historial(max_muestras, intervalo)
        self.historial.limpiar()

    @staticmethod
    def _reiniciar_estado():
        """Cada corrida empieza con el PID y las perturbaciones en cero."""
        vpid.error_prev = 0.0
        vpid.medida_prev = None
        vpid.integral = 0.0
        vpid.derivada = 0.0
        vpid.proporcional = 0.0
        reiniciar_impulso()

    # ---- un paso de simulación --------------------------------------
    def paso(self):
        error = construir_error(self.t, self.T)
        u = actualizar_pid(error, vhorno.T_SET - error)   # medida = lo que "lee" el controlador
        # se registra ANTES de integrar: cada muestra es coherente en el
        # instante t (T(t), el error visto en t y la u decidida en t)
        self.historial.registrar(self.t, self.T, error, u)
        self.T = self._integrar(self.T, u)
        self.t += vhorno.DT
        self.u, self.error = u, error
        return u, error

    def avanzar(self, pasos):
        """Ejecuta ``pasos`` pasos seguidos."""
        for _ in range(pasos):
            self.paso()
