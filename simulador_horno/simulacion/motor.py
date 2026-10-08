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
from simulador_horno.modelo import horno as modelo_horno
from simulador_horno.modelo.perturbaciones import (
    factor_potencia_red, impulso_activo, puerta, reiniciar_impulso, temperatura_ambiente,
)
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
        self.impulsos = 0   # impulsos ocurridos en la corrida (la interfaz los avisa)
        self.aperturas = 0  # aperturas de puerta en la corrida
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
        puerta.reiniciar()

    # ---- un paso de simulación --------------------------------------
    def paso(self):
        error, impulso_nuevo = construir_error(self.t, self.T)
        if impulso_nuevo:
            self.impulsos += 1
        u = actualizar_pid(error, vhorno.T_SET - error)   # medida = lo que "lee" el controlador
        # se registra ANTES de integrar: cada muestra es coherente en el
        # instante t (T(t), el error visto en t y la u decidida en t)
        self.historial.registrar(self.t, self.T, error, u)
        entorno = self._entorno()
        if entorno is modelo_horno.ENTORNO_IDEAL:
            self.T = self._integrar(self.T, u)
        else:
            # las perturbaciones del horno solo rigen durante este paso
            modelo_horno.entorno = entorno
            try:
                self.T = self._integrar(self.T, u)
            finally:
                modelo_horno.entorno = modelo_horno.ENTORNO_IDEAL
        self.t += vhorno.DT
        self.u, self.error = u, error
        return u, error

    def _entorno(self):
        """Condiciones físicas del paso según las perturbaciones del horno activas."""
        if not (vhorno.puerta or vhorno.red_variable or vhorno.ambiente_variable):
            return modelo_horno.ENTORNO_IDEAL
        T_amb, perdida_extra, potencia = None, 0.0, 1.0
        if vhorno.ambiente_variable:
            T_amb = temperatura_ambiente(self.t, vhorno.T_AMB,
                                         limites.AMBIENTE_AMPLITUD, limites.AMBIENTE_PERIODO)
        if vhorno.red_variable:
            potencia = factor_potencia_red(self.t, limites.RED_AMPLITUDES, limites.RED_PERIODOS)
        if vhorno.puerta:
            abierta, nueva = puerta.actualizar(self.t, vhorno.DT,
                                               limites.TASA_PUERTA_HORA, limites.DURACION_PUERTA)
            self.aperturas += nueva
            if abierta:
                perdida_extra = 1.0 / limites.TAU_PUERTA
        return (T_amb, perdida_extra, potencia)

    @property
    def puerta_abierta(self):
        return vhorno.puerta and puerta.activo

    @property
    def impulso_activo(self):
        return vhorno.flag_error and impulso_activo()

    def avanzar(self, pasos):
        """Ejecuta ``pasos`` pasos seguidos."""
        for _ in range(pasos):
            self.paso()
