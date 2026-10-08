"""Motor de la simulación: la lógica de cada paso, sin consola ni ventana.

Separado de la interfaz para poder probarlo con pytest en un entorno sin
pantalla y para que la velocidad de ejecución no altere los resultados:
el motor solo sabe de pasos de ``DT`` simulado.
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.configuracion import parametros_simulacion as vsim
from simulador_horno.control.pid import PID
from simulador_horno.control.senal_error import construir_error
from simulador_horno.modelo.perturbaciones import Perturbador
from simulador_horno.numerico.integradores import METODOS
from simulador_horno.simulacion.historial import Historial


class Motor:
    """Estado de una corrida: temperatura, tiempo simulado e historial.

    ``semilla`` fija el generador aleatorio de las perturbaciones (None =
    una corrida distinta cada vez).
    """

    def __init__(self, max_muestras=limites.MAX_MUESTRAS, intervalo=limites.INTERVALO_MUESTREO,
                 semilla=None):
        vhorno.recalcular_B()
        self.pid = PID(vpid)   # cada corrida empieza con el PID en cero
        self.perturbador = Perturbador(semilla)
        self.metodo = vsim.metodo
        self._integrar = METODOS[self.metodo]   # Euler, Heun o RK4, fijo durante la corrida
        self.T = vhorno.T_INICIAL   # T_AMB = arranque en frío; mayor = en caliente
        self.t = 0.0
        self.u = 0.0
        self.error = vhorno.T_SET - self.T
        self.impulsos = 0   # impulsos ocurridos en la corrida (la interfaz los avisa)
        self.aperturas = 0  # aperturas de puerta en la corrida
        self.historial = Historial(max_muestras, intervalo)
        self.historial.limpiar()

    # ---- un paso de simulación --------------------------------------
    def paso(self):
        error, impulso_nuevo = construir_error(self.t, self.T, vhorno.T_SET, vhorno.DT,
                                               vhorno, self.perturbador)
        if impulso_nuevo:
            self.impulsos += 1
        u = self.pid.paso(error, vhorno.T_SET - error, vhorno.DT)   # medida = lo que "lee" el controlador
        # se registra ANTES de integrar: cada muestra es coherente en el
        # instante t (T(t), el error visto en t y la u decidida en t)
        self.historial.registrar(self.t, self.T, error, u)
        # las perturbaciones del horno solo rigen durante este paso
        entorno, apertura = self.perturbador.entorno(self.t, vhorno.DT, vhorno.T_AMB, vhorno)
        self.aperturas += apertura
        self.T = self._integrar(self.T, u, vhorno, entorno)
        self.t += vhorno.DT
        self.u, self.error = u, error
        return u, error

    @property
    def puerta_abierta(self):
        return vhorno.puerta and self.perturbador.puerta.activo

    @property
    def impulso_activo(self):
        return vhorno.flag_error and self.perturbador.impulso.activo

    def avanzar(self, pasos):
        """Ejecuta ``pasos`` pasos seguidos."""
        for _ in range(pasos):
            self.paso()
