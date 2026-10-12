"""Parámetros configurables del simulador, como objetos con su propio estado.

Cada ``Simulador`` tiene su propia ``Configuracion``: en un servidor web
cada sesión de usuario edita la suya sin afectar a las demás (antes eran
variables de módulo compartidas por todo el proceso).

Los valores por defecto son la configuración de fábrica del simulador.
Las constantes que el usuario NO edita siguen en ``limites``.
"""
from copy import deepcopy
from dataclasses import dataclass, field

from simulador_horno.configuracion import limites


@dataclass
class ParametrosHorno:
    T_AMB: float = 30.0        # temperatura ambiente (°C)
    T_SET: float = 1000.0      # setpoint / temperatura objetivo (°C)
    T_MAX_EQ: float = 1300.0   # equilibrio a potencia plena, u = 1 (°C)
    T_INICIAL: float = 30.0    # temperatura al empezar la corrida (°C); = T_AMB es arranque en frío
    TAU: float = 3000          # constante de tiempo del horno (s)
    DT: float = 0.1            # paso de integración (s); fijo, NO acelera la simulación

    @property
    def B(self):
        """Ganancia térmica derivada (°C/s por unidad de control), no editable.

        En equilibrio con u = 1, dT/dt = 0  ->  B = (T_MAX_EQ − T_AMB) / TAU
        """
        tau = self.TAU if self.TAU > 0 else 1e-6   # evita división por cero
        return (self.T_MAX_EQ - self.T_AMB) / tau


@dataclass
class ParametrosPID:
    KP: float = 200   # ganancia proporcional
    KI: float = 10    # ganancia integral
    KD: float = 2000  # ganancia derivativa (antes 2: su aporte era invisible, 0,004 %)
    # "ninguno" | "recorte" | "condicional"   (ver control.anti_windup)
    anti_windup: str = "condicional"
    # factor [0, 1] del modo "recorte": escala la integral cuando supera
    # limites.UMBRAL_INTEGRAL
    restringir_integral: float = 0.85
    # constante del filtro de la derivada (s): suaviza el ruido del sensor; 0 = sin filtro
    filtro_derivada: float = 10.0
    # "automatico": el PID decide u (sin pasar de limite_potencia);
    # "manual": u = potencia_manual, fijada por el usuario (lazo abierto)
    modo_control: str = "automatico"
    potencia_manual: float = 0.5     # fracción [0, 1] en modo manual
    limite_potencia: float = 1.0     # máxima fracción que el PID puede pedir


@dataclass
class Perturbaciones:
    """Conmutadores de las perturbaciones (todas apagadas por defecto).

    Los nombres coinciden con ``limites.PERTURBACIONES``; las constantes de
    cada una (tasas, amplitudes...) están en ``limites``.
    """
    # sobre la MEDICIÓN (el controlador lee mal; el horno no cambia)
    error_oscilante: bool = False   # ruido + senoide sobre el error
    flag_error: bool = False        # impulsos probabilísticos sobre el error
    ruido_termopar: bool = False    # ruido gaussiano en la lectura del termopar
    # sobre el HORNO (física real)
    puerta: bool = False            # aperturas de puerta al azar: más pérdidas
    red_variable: bool = False      # fluctuación del voltaje de red: potencia ∝ V²
    ambiente_variable: bool = False # temperatura ambiente que oscila lentamente
    tasa_impulsos_hora: float = limites.TASA_IMPULSOS_HORA   # impulsos por hora simulada


@dataclass
class ParametrosActuador:
    """El triac que gobierna la potencia (ver ``modelo.triac``)."""
    # interruptor de potencia: apagado corta la energía a la resistencia, pero el
    # control (termopar, PID, disparo del triac) sigue funcionando
    encendido: bool = True
    modo: str = "ideal"               # ideal | triac_lineal | triac_compensado
    metodo: str = "newton"            # inversión de la curva: newton | biseccion
    V_red: float = 220.0              # voltaje eficaz de la red (V)
    frecuencia: float = 60.0          # Hz (un disparo por medio ciclo)
    potencia_nominal: float = 3000.0  # W con el triac abierto del todo
    alfa_min: float = limites.THETA_MIN   # grados: límites físicos del disparo
    alfa_max: float = limites.THETA_MAX
    resolucion: float = 0.0           # grados del temporizador de disparo (0 = continuo)
    dispersion: float = 0.0           # grados: desviación típica del instante de disparo

    @property
    def R(self):
        """Resistencia del horno (Ω): V_red² / potencia nominal."""
        return self.V_red * self.V_red / self.potencia_nominal


@dataclass
class ParametrosSimulacion:
    velocidad: str = "x60"            # clave de limites.VELOCIDADES
    duracion_horas: float | None = 2  # horas simuladas; None = sin límite
    metodo: str = "euler"             # clave de numerico.integradores.METODOS


@dataclass
class Configuracion:
    """Todo lo que el usuario puede cambiar, agrupado."""
    horno: ParametrosHorno = field(default_factory=ParametrosHorno)
    pid: ParametrosPID = field(default_factory=ParametrosPID)
    perturbaciones: Perturbaciones = field(default_factory=Perturbaciones)
    simulacion: ParametrosSimulacion = field(default_factory=ParametrosSimulacion)
    actuador: ParametrosActuador = field(default_factory=ParametrosActuador)

    def copia(self):
        """Copia independiente (para comparar corridas o clonar una sesión)."""
        return deepcopy(self)
