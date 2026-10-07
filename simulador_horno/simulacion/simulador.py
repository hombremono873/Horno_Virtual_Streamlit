"""Orquestación del bucle de simulación del horno.

Cada iteración: construir error -> PID -> avanzar la planta -> registrar
historial -> refrescar tabla de consola y monitor gráfico -> esperar el
resto del paso. La simulación termina con Ctrl+C o al cerrar la ventana.
"""
import time

from rich.live import Live

from simulador_horno.config import limites, tema
from simulador_horno.config import parametros_horno as vhorno
from simulador_horno.config import parametros_pid as vpid
from simulador_horno.control.controlador.pid import actualizar_pid
from simulador_horno.control.modelo_termico.horno import simular_horno
from simulador_horno.control.perturbaciones.senal_error import construir_error
from simulador_horno.interfaces.consola import marco
from simulador_horno.interfaces.consola.tabla_vivo import generar_tabla
from simulador_horno.interfaces.graficas.panel import PanelGraficas
from simulador_horno.simulacion.historial import Historial


class Simulador:
    """Ejecuta la simulación del calentamiento del horno con control PID."""

    def __init__(self, max_muestras=limites.MAX_MUESTRAS):
        self.T = vhorno.T_AMB
        self.t = 0.0
        self.historial = Historial(max_muestras)
        self.panel = None

    # ---- un paso de simulación --------------------------------------
    def paso(self):
        error = construir_error(self.t, self.T)
        u = actualizar_pid(error)
        self.T = simular_horno(self.T, u)
        self.historial.registrar(self.t, self.T, error)
        self.t += vhorno.DT
        return u, error

    # ---- bucle completo -------------------------------------------
    def ejecutar(self):
        self.panel = PanelGraficas()
        interrumpido = False
        try:
            with Live(screen=True, refresh_per_second=limites.REFRESCO_HZ, console=marco.console) as live:
                while True:
                    inicio = time.monotonic()
                    u, error = self.paso()
                    live.update(self._tabla(u, error))
                    self.panel.actualizar(
                        self.historial.tiempos, self.historial.temperaturas,
                        self.historial.errores, self.T, vhorno.T_SET,
                    )
                    if not self.panel.abierta:
                        break
                    self._dormir_resto(inicio)
        except KeyboardInterrupt:
            interrumpido = True
        finally:
            self._finalizar(interrumpido)

    # ---- helpers --------------------------------------------------
    def _tabla(self, u, error):
        acciones = {"P": vpid.proporcional, "I": vpid.integral, "D": vpid.derivada}
        return generar_tabla(
            self.t, self.T, vhorno.T_SET, u, error,
            pid={"kp": vpid.KP, "ki": vpid.KI, "kd": vpid.KD},
            horno={"B": vhorno.B, "tau": vhorno.TAU, "T_amb": vhorno.T_AMB, "dt": vhorno.DT},
            acciones=acciones,
        )

    def _dormir_resto(self, inicio):
        transcurrido = time.monotonic() - inicio
        time.sleep(max(0.0, vhorno.DT - transcurrido))

    def _finalizar(self, interrumpido):
        motivo = "interrumpida por el usuario" if interrumpido else "ventana del monitor cerrada"
        marco.console.clear()
        marco.console.print(f"[{tema.C_AVISO}]Simulación detenida — {motivo}.[/]")

        if self.panel is not None and self.panel.abierta:
            marco.console.print(
                f"[{tema.C_TENUE}]Revisa el monitor; pulsa una tecla para volver al menú.[/]"
            )
            try:
                marco.leer_tecla()
            except KeyboardInterrupt:
                pass

        if self.panel is not None:
            self.panel.cerrar()
        self.historial.limpiar()
