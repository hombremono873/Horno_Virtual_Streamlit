"""Generación de perturbaciones sobre el sistema.

Incluye ruido aleatorio, una componente senoidal suave, un impulso térmico
probabilístico de signo alternante y las perturbaciones físicas del horno
(puerta, red eléctrica y ambiente).

Todo se expresa en tiempo SIMULADO para que el resultado no dependa del
paso de integración ``dt``: los eventos se definen por una tasa por hora y
se convierten a probabilidad por paso con

    p = 1 - exp(-tasa * dt)

(probabilidad de al menos un evento de Poisson en un intervalo ``dt``).

Sin estado global: los números aleatorios salen del generador ``rng`` que
se recibe (``random.Random``) y el estado de los eventos vive en objetos.
``Perturbador`` reúne ambos para una corrida; con la misma semilla la
corrida se repite exactamente.
"""
import math
import random

from simulador_horno.configuracion import limites
from simulador_horno.modelo.horno import ENTORNO_IDEAL


def probabilidad_por_paso(tasa_hora, dt):
    """Probabilidad de que ocurra un evento en un paso ``dt`` (s)."""
    return 1.0 - math.exp(-(tasa_hora / 3600.0) * dt)


class Impulso:
    """Impulso que aparece con ``tasa_hora`` eventos/hora y dura ``duracion`` s.

    El signo se mantiene durante todo el impulso y se invierte de un
    impulso al siguiente (el primero es negativo).
    """

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        """Olvida cualquier impulso en curso (al empezar cada corrida)."""
        self.activo = False
        self.t_inicio = 0
        self.signo = 1

    def actualizar(self, t, dt, tasa_hora, duracion, magnitud, rng):
        """Devuelve ``(valor, activo, nuevo)``; ``nuevo`` es True solo en el
        paso en que el impulso comienza."""
        if self.activo:
            if t < self.t_inicio + duracion:
                return self.signo * abs(magnitud), True, False
            self.activo = False
            return 0, False, False

        if rng.random() < probabilidad_por_paso(tasa_hora, dt):
            self.activo = True
            self.t_inicio = t
            self.signo *= -1
            return self.signo * abs(magnitud), True, True

        return 0, False, False


class EventoAleatorio:
    """Evento que ocurre ``tasa_hora`` veces por hora simulada y dura
    ``duracion`` segundos (con la misma conversión a probabilidad por paso
    que el impulso, de modo que no depende de ``dt``)."""

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.activo = False
        self.t_inicio = 0.0

    def actualizar(self, t, dt, tasa_hora, duracion, rng):
        """Devuelve ``(activo, nuevo)``."""
        if self.activo:
            if t < self.t_inicio + duracion:
                return True, False
            self.activo = False
        if rng.random() < probabilidad_por_paso(tasa_hora, dt):
            self.activo, self.t_inicio = True, t
            return True, True
        return False, False


def ruido_oscilante(t, rng):
    """Ruido leve sobre la medición: senoide suave + ruido uniforme."""
    ruido = rng.uniform(-0.5, 1.5)
    perturbacion = 20 * math.sin(0.05 * t)
    return perturbacion + ruido


def factor_potencia_red(t, amplitudes, periodos):
    """Fracción de la potencia nominal: (V/Vn)², con V/Vn = 1 + Σ a·sen(2πt/P + fase)."""
    v = 1.0
    for i, (a, p) in enumerate(zip(amplitudes, periodos)):
        v += a * math.sin(2 * math.pi * t / p + i)   # fase distinta por armónico
    return v * v


def temperatura_ambiente(t, T_amb, amplitud, periodo):
    """Ambiente que oscila lentamente alrededor de ``T_amb``."""
    return T_amb + amplitud * math.sin(2 * math.pi * t / periodo)


class Perturbador:
    """Generador aleatorio y estado de las perturbaciones de UNA corrida.

    ``semilla=None`` toma la semilla del sistema (corridas distintas cada
    vez); con una semilla entera la corrida es reproducible.
    """

    def __init__(self, semilla=None):
        self.impulso = Impulso()
        self.puerta = EventoAleatorio()
        self.reiniciar(semilla)

    def reiniciar(self, semilla=None):
        self.rng = random.Random(semilla)
        self.impulso.reiniciar()
        self.puerta.reiniciar()
        self.ultimo_impulso = 0.0   # perturbación de la última llamada a perturbacion_total

    # ---- sobre la MEDICIÓN ---------------------------------------------
    def ruido_termopar(self, sigma=limites.RUIDO_TERMOPAR_SIGMA):
        """Error de lectura del termopar (°C), gaussiano de media cero."""
        return self.rng.gauss(0.0, sigma)

    def ruido_oscilante(self, t):
        return ruido_oscilante(t, self.rng)

    def perturbacion_total(self, t, dt, tasa_hora=limites.TASA_IMPULSOS_HORA,
                           duracion=limites.DURACION_IMPULSO, magnitud=limites.MAGNITUD_IMPULSO):
        """Ruido + senoide + impulso en el instante ``t``. Devuelve ``(total, impulso_nuevo)``."""
        ruido = self.rng.uniform(-0.5, 1.5)
        senoide = 20 * math.sin(0.05 * t)
        impulso, _, nuevo = self.impulso.actualizar(t, dt, tasa_hora, duracion, magnitud, self.rng)
        self.ultimo_impulso = ruido + senoide + impulso
        return self.ultimo_impulso, nuevo

    # ---- sobre el HORNO ------------------------------------------------
    def entorno(self, t, dt, T_amb, perturbaciones):
        """Condiciones físicas del paso según las perturbaciones del horno activas.

        Devuelve ``(entorno, apertura_nueva)``; ``entorno`` es
        ``ENTORNO_IDEAL`` si ninguna está activa.
        """
        p = perturbaciones
        if not (p.puerta or p.red_variable or p.ambiente_variable):
            return ENTORNO_IDEAL, False
        T_amb_efectiva, perdida_extra, potencia = None, 0.0, 1.0
        nueva = False
        if perturbaciones.ambiente_variable:
            T_amb_efectiva = temperatura_ambiente(t, T_amb, limites.AMBIENTE_AMPLITUD,
                                                  limites.AMBIENTE_PERIODO)
        if perturbaciones.red_variable:
            potencia = factor_potencia_red(t, limites.RED_AMPLITUDES, limites.RED_PERIODOS)
        if perturbaciones.puerta:
            abierta, nueva = self.puerta.actualizar(t, dt, limites.TASA_PUERTA_HORA,
                                                    limites.DURACION_PUERTA, self.rng)
            if abierta:
                perdida_extra = 1.0 / limites.TAU_PUERTA
        return (T_amb_efectiva, perdida_extra, potencia), nueva
