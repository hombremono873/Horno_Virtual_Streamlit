"""Orquestación del bucle de simulación del horno.

En cada refresco de pantalla (``REFRESCO_HZ`` veces por segundo real) se
ejecutan N pasos del motor, con N elegido según la velocidad activa
(ver ``reloj.pasos_por_refresco``); después se refrescan la tabla de
consola y el monitor gráfico y se espera el resto del refresco. En modo
"máxima" no se espera: se calculan pasos durante todo el refresco.

La simulación termina con Ctrl+C o al cerrar la ventana.
"""
import time

from rich.live import Live

from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as vhorno
from simulador_horno.configuracion import parametros_pid as vpid
from simulador_horno.configuracion import parametros_simulacion as vsim
from simulador_horno.estilos import tema
from simulador_horno.interfaz.consola import marco
from simulador_horno.interfaz.consola.tabla_vivo import generar_tabla
from simulador_horno.interfaz.graficas.panel import PanelGraficas
from simulador_horno.simulacion.motor import Motor
from simulador_horno.simulacion.reloj import pasos_por_refresco

LOTE_MAXIMA = 200   # pasos entre consultas al reloj en modo "máxima"


class Simulador:
    """Ejecuta la simulación del calentamiento del horno con control PID."""

    def __init__(self, max_muestras=limites.MAX_MUESTRAS):
        self.motor = Motor(max_muestras)
        self.panel = None
        self._acumulado = 0.0
        self._inicio_real = None

    # ---- un refresco: N pasos según la velocidad ---------------------
    def _avanzar_refresco(self, inicio, periodo):
        factor = limites.VELOCIDADES.get(vsim.velocidad, 60)
        if factor is None:
            while time.monotonic() - inicio < periodo:
                self.motor.avanzar(LOTE_MAXIMA)
            return
        pasos, self._acumulado = pasos_por_refresco(
            factor, vhorno.DT, limites.REFRESCO_HZ, self._acumulado
        )
        self.motor.avanzar(pasos)

    # ---- bucle completo -------------------------------------------
    def ejecutar(self):
        self.panel = PanelGraficas()
        periodo = 1.0 / limites.REFRESCO_HZ
        self._inicio_real = time.monotonic()
        interrumpido = False
        try:
            with Live(screen=True, refresh_per_second=limites.REFRESCO_HZ, console=marco.console) as live:
                while True:
                    inicio = time.monotonic()
                    self._avanzar_refresco(inicio, periodo)
                    live.update(self._tabla())
                    historial = self.motor.historial
                    self.panel.actualizar(
                        historial.tiempos, historial.temperaturas,
                        historial.errores, self.motor.T, vhorno.T_SET,
                    )
                    if not self.panel.abierta:
                        break
                    self._dormir_resto(inicio, periodo)
        except KeyboardInterrupt:
            interrumpido = True
        finally:
            self._finalizar(interrumpido)

    # ---- helpers --------------------------------------------------
    def _tabla(self):
        m = self.motor
        acciones = {"P": vpid.proporcional, "I": vpid.integral, "D": vpid.derivada}
        return generar_tabla(
            m.t, m.T, vhorno.T_SET, m.u, m.error,
            pid={"kp": vpid.KP, "ki": vpid.KI, "kd": vpid.KD},
            horno={"B": vhorno.B, "tau": vhorno.TAU, "T_amb": vhorno.T_AMB,
                   "T_max_eq": vhorno.T_MAX_EQ, "dt": vhorno.DT},
            acciones=acciones,
            velocidad=vsim.velocidad,
            t_real=time.monotonic() - self._inicio_real,
        )

    @staticmethod
    def _dormir_resto(inicio, periodo):
        transcurrido = time.monotonic() - inicio
        time.sleep(max(0.0, periodo - transcurrido))

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
        self.motor.historial.limpiar()
