"""Simulador: una corrida del horno con control PID, sin E/S.

Reúne todo el estado de una corrida en un objeto: su ``Configuracion``, el
``PID``, el ``Perturbador`` (con su generador aleatorio) y el ``Historial``.
Dos simuladores no comparten nada, así que en la web cada sesión de usuario
tiene el suyo.

La interfaz decide CUÁNTOS pasos ejecutar (según la velocidad, ver
``reloj``) y cómo mostrar los resultados; aquí solo hay pasos de ``DT``
simulado, de modo que la velocidad nunca altera los resultados.

La configuración se lee en cada paso: cambiar el setpoint o una ganancia
afecta a la corrida en curso. El método numérico y la duración se fijan al
empezar la corrida (``reiniciar``). Modifica los campos de
``config.horno``, ``config.pid``... en sitio; no reemplaces esos objetos.
"""
import math

from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import Configuracion
from simulador_horno.control.pid import PID
from simulador_horno.control.senal_error import construir_error
from simulador_horno.modelo.perturbaciones import Perturbador
from simulador_horno.modelo.triac import Triac, energia_kwh
from simulador_horno.numerico.integradores import METODOS
from simulador_horno.simulacion import metricas
from simulador_horno.simulacion.historial import Historial
from simulador_horno.simulacion.reloj import pasos_restantes


class Simulador:
    """Estado de una corrida: temperatura, tiempo simulado, controlador e historial.

    ``semilla`` fija el generador aleatorio de las perturbaciones: con la
    misma semilla y la misma configuración la corrida se repite exactamente.
    None = una corrida distinta cada vez.
    """

    def __init__(self, configuracion=None, semilla=None,
                 max_muestras=limites.MAX_MUESTRAS, intervalo=limites.INTERVALO_MUESTREO):
        self.config = configuracion if configuracion is not None else Configuracion()
        self.semilla = semilla
        self.pid = PID(self.config.pid)
        self.perturbador = Perturbador(semilla)
        self.triac = Triac(self.config.actuador)
        self.historial = Historial(max_muestras, intervalo)
        self.reiniciar()

    def reiniciar(self):
        """Empieza una corrida nueva con la configuración actual."""
        horno, sim = self.config.horno, self.config.simulacion
        self.pid.parametros = self.config.pid
        self.pid.reiniciar()
        self.perturbador.reiniciar(self.semilla)
        self.metodo = sim.metodo
        self._integrar = METODOS[self.metodo]   # Euler, Heun o RK4, fijo durante la corrida
        horas = sim.duracion_horas
        self.duracion = None if horas is None else horas * 3600.0   # s simulados; fija por corrida
        self.T = horno.T_INICIAL   # T_AMB = arranque en frío; mayor = en caliente
        self.t = 0.0
        self.u = 0.0
        self.error = horno.T_SET - self.T
        self.impulsos = 0   # impulsos ocurridos en la corrida (la interfaz los avisa)
        self.aperturas = 0  # aperturas de puerta en la corrida
        self.triac.parametros = self.config.actuador
        self.energia_j = 0.0        # energía eléctrica consumida (J)
        self.alfa, self.fraccion, self.potencia_w, self.iteraciones = math.nan, 0.0, 0.0, 0
        self.historial.limpiar()

    # ---- un paso de simulación --------------------------------------
    def paso(self):
        horno, perturbaciones = self.config.horno, self.config.perturbaciones
        error, impulso_nuevo = construir_error(self.t, self.T, horno.T_SET, horno.DT,
                                               perturbaciones, self.perturbador)
        if impulso_nuevo:
            self.impulsos += 1
        pid = self.pid
        medida = horno.T_SET - error   # lo que "lee" el controlador
        if pid.parametros.modo_control == "manual":
            # lazo abierto: el usuario fija la potencia; el PID solo la sigue
            u = min(max(pid.parametros.potencia_manual, 0.0), 1.0)
            pid.seguir(u, error, medida, horno.DT)
        else:
            u = pid.paso(error, medida, horno.DT, cortada=not self.config.actuador.encendido)
        # las perturbaciones del horno solo rigen durante este paso
        entorno, apertura = self.perturbador.entorno(self.t, horno.DT, horno.T_AMB, perturbaciones)
        self.aperturas += apertura
        # el triac convierte la u pedida en la fracción de potencia que llega
        # (en modo ideal es la misma u). Su dispersión usa el generador
        # DESPUÉS de las perturbaciones: el orden de las corridas no cambia.
        fraccion, alfa, iteraciones = self.triac.aplicar(u, self.perturbador.rng)
        if not self.config.actuador.encendido:
            fraccion = 0.0      # interruptor apagado: el triac dispara pero no llega energía
        potencia_w = fraccion * self.config.actuador.potencia_nominal * entorno[2]   # entorno[2] = (V/Vn)²
        # se registra ANTES de integrar: cada muestra es coherente en el
        # instante t (T(t), el error visto en t y la u decidida en t)
        self.historial.registrar(
            self.t, self.T, error, u, horno.T_SET,
            pid.proporcional / limites.U_MAX,
            pid.parametros.KI * pid.integral / limites.U_MAX,
            pid.derivada / limites.U_MAX,
            alfa=alfa, fraccion=fraccion, potencia_w=potencia_w, energia_kwh=energia_kwh(self.energia_j),
        )
        self.energia_j += potencia_w * horno.DT
        self.T = self._integrar(self.T, fraccion, horno, entorno)
        self.t += horno.DT
        self.u, self.error = u, error
        self.alfa, self.fraccion, self.potencia_w, self.iteraciones = alfa, fraccion, potencia_w, iteraciones
        return u, error

    def avanzar(self, pasos):
        """Ejecuta ``pasos`` pasos seguidos (sin mirar la duración)."""
        for _ in range(pasos):
            self.paso()

    # ---- duración de la corrida -------------------------------------
    @property
    def pasos_restantes(self):
        """Pasos que faltan para completar la duración; None si no tiene límite."""
        return pasos_restantes(self.t, self.duracion, self.config.horno.DT)

    @property
    def terminada(self):
        """True cuando se completó la duración elegida."""
        return self.pasos_restantes == 0

    def avanzar_sin_pasarse(self, pasos):
        """Como ``avanzar``, pero se detiene al completar la duración. Devuelve los pasos dados."""
        restantes = self.pasos_restantes
        if restantes is not None:
            pasos = min(pasos, restantes)
        self.avanzar(pasos)
        return pasos

    def completar(self):
        """Ejecuta lo que falta de la corrida ("corrida completa")."""
        if self.duracion is None:
            raise ValueError("una corrida sin límite de duración no se puede completar")
        self.avanzar(self.pasos_restantes)

    # ---- estado para la interfaz ------------------------------------
    @property
    def puerta_abierta(self):
        return self.config.perturbaciones.puerta and self.perturbador.puerta.activo

    @property
    def impulso_activo(self):
        return self.config.perturbaciones.flag_error and self.perturbador.impulso.activo

    def metricas(self):
        """Métricas de desempeño de lo simulado hasta ahora (None si no hay datos)."""
        h = self.historial
        return metricas.calcular(h.tiempos, h.temperaturas, self.config.horno.T_SET)

    def parametros_corrida(self):
        """Configuración de la corrida, para guardarla junto a los datos."""
        horno, pid, sim = self.config.horno, self.config.pid, self.config.simulacion
        return {
            "metodo": self.metodo,
            "dt": float(horno.DT),
            "anti_windup": pid.anti_windup,
            "factor_recorte": float(pid.restringir_integral) if pid.anti_windup == "recorte" else None,
            "KP": pid.KP, "KI": pid.KI, "KD": pid.KD,
            "T_AMB": horno.T_AMB, "T_INICIAL": horno.T_INICIAL,
            "T_SET": horno.T_SET, "T_MAX_EQ": horno.T_MAX_EQ,
            "TAU": horno.TAU, "B": float(horno.B),
            "velocidad": sim.velocidad,
            "duracion_h": sim.duracion_horas,
            "semilla": self.semilla,
            "corrida_completa": "si" if self.terminada else "no",
            **{f"perturbacion_{a}": "si" if getattr(self.config.perturbaciones, a) else "no"
               for a, _, _ in limites.PERTURBACIONES},
            "modo_control": pid.modo_control,
            "limite_potencia": pid.limite_potencia,
            "potencia_manual": pid.potencia_manual if pid.modo_control == "manual" else None,
            "encendido": "si" if self.config.actuador.encendido else "no",
            "actuador": self.config.actuador.modo,
            "metodo_inversion": self.config.actuador.metodo,
            "V_red": self.config.actuador.V_red,
            "potencia_nominal_W": self.config.actuador.potencia_nominal,
            "energia_kWh": energia_kwh(self.energia_j),
            "tasa_impulsos_hora": self.config.perturbaciones.tasa_impulsos_hora,
            "impulsos_ocurridos": self.impulsos,
            "aperturas_de_puerta": self.aperturas,
        }
