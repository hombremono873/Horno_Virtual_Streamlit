"""Triac: el actuador que gobierna la potencia eléctrica del horno.

La resistencia del horno se alimenta con la red alterna. En cada medio
ciclo el triac espera un ÁNGULO DE DISPARO α (0° a 180°) y conduce desde
ahí hasta el final del medio ciclo:

    α = 0°    conduce todo el medio ciclo    -> potencia máxima
    α = 90°   conduce la mitad               -> la mitad de la potencia
    α = 180°  no conduce                     -> apagado

La potencia NO es proporcional al ángulo. Con α en grados:

    fracción de potencia = 1 − α/180 + sen(2α) / (2π)

Por eso convertir la señal del PID en ángulo "en línea recta"
(α = 180·(1 − u)) entrega otra potencia que la pedida: con u = 0,764 da
el 92,3 %. Para que el horno reciba lo que pide el PID hay que INVERTIR la
curva: hallar α tal que fracción(α) = u. La ecuación es trascendente (no
se despeja), así que se resuelve con métodos numéricos: bisección o
Newton-Raphson.

Todas las funciones son puras (sin estado global ni interfaz). El
generador aleatorio de la dispersión del disparo se recibe como argumento.
"""
import math

ALFA_APAGADO = 180.0    # sin disparo: el triac no conduce
TOLERANCIA = 1e-9       # grados: precisión de la inversión numérica
MAX_ITERACIONES = 200

MODOS = {
    "ideal": "Ideal (potencia = u)",
    "triac_lineal": "Triac, ángulo lineal",
    "triac_compensado": "Triac compensado (curva invertida)",
}
METODOS_INVERSION = {"newton": "Newton-Raphson", "biseccion": "Bisección"}


# ======================================================================
# La curva del triac
# ======================================================================
def fraccion_potencia(alfa):
    """Fracción de la potencia máxima que entrega el triac con ángulo ``alfa`` (grados)."""
    alfa = min(max(alfa, 0.0), 180.0)
    # max(0, …): en 180° el redondeo daría −2e-17 (y la raíz del voltaje eficaz fallaría)
    return max(0.0, 1.0 - alfa / 180.0 + math.sin(2.0 * math.radians(alfa)) / (2.0 * math.pi))


def derivada_fraccion(alfa):
    """d(fracción)/dα, por grado: −2·sen²(α)/180. Vale 0 en 0° y 180° (curva plana)."""
    s = math.sin(math.radians(alfa))
    return -2.0 * s * s / 180.0


def resistencia(potencia_nominal, V_red):
    """Resistencia del horno (Ω) que da la potencia nominal con el triac abierto del todo."""
    return V_red * V_red / potencia_nominal


def voltaje_rms(alfa, V_red):
    """Voltaje eficaz sobre la resistencia: V_red · raíz(fracción)."""
    return V_red * math.sqrt(fraccion_potencia(alfa))


def potencia_electrica(alfa, V_red, R):
    """Potencia (W) que disipa la resistencia: V_red²/R · fracción."""
    return V_red * V_red / R * fraccion_potencia(alfa)


# ======================================================================
# De la señal de control u al ángulo de disparo
# ======================================================================
def _acotar_u(u):
    return min(max(u, 0.0), 1.0)


def angulo_lineal(u):
    """Conversión ingenua: α = 180·(1 − u). Entrega otra potencia que la pedida."""
    return 180.0 * (1.0 - _acotar_u(u))


def angulo_por_biseccion(u, tol=TOLERANCIA):
    """Ángulo α con fracción(α) = u, por bisección. Devuelve ``(α, iteraciones)``.

    La curva decrece de 1 (en 0°) a 0 (en 180°): siempre hay una raíz en
    [0, 180] y cada iteración parte el intervalo a la mitad.
    """
    u = _acotar_u(u)
    if u <= 0.0:
        return ALFA_APAGADO, 0
    if u >= 1.0:
        return 0.0, 0
    bajo, alto, iteraciones = 0.0, 180.0, 0
    while alto - bajo > tol and iteraciones < MAX_ITERACIONES:
        medio = 0.5 * (bajo + alto)
        if fraccion_potencia(medio) > u:
            bajo = medio        # todavía da más potencia de la pedida: hay que disparar más tarde
        else:
            alto = medio
        iteraciones += 1
    return 0.5 * (bajo + alto), iteraciones


def angulo_por_newton(u, tol=TOLERANCIA):
    """Ángulo α con fracción(α) = u, por Newton-Raphson protegido. Devuelve ``(α, iteraciones)``.

    α_nuevo = α − (fracción(α) − u) / derivada(α)

    Cerca de 0° y de 180° la curva es casi plana (derivada ≈ 0) y el paso
    de Newton se dispara fuera del intervalo; en ese caso se da un paso de
    bisección dentro del intervalo que contiene la raíz.
    """
    u = _acotar_u(u)
    if u <= 0.0:
        return ALFA_APAGADO, 0
    if u >= 1.0:
        return 0.0, 0
    bajo, alto = 0.0, 180.0
    alfa = angulo_lineal(u)         # punto de partida razonable
    for iteraciones in range(1, MAX_ITERACIONES + 1):
        g = fraccion_potencia(alfa) - u
        if g == 0.0:
            return alfa, iteraciones
        if g > 0:
            bajo = alfa
        else:
            alto = alfa
        d = derivada_fraccion(alfa)
        nuevo = alfa - g / d if d != 0.0 else math.inf
        if abs(nuevo - alfa) <= tol:            # convergió (se comprueba antes del respaldo:
            return nuevo, iteraciones           # en la raíz el paso cae en el borde del intervalo)
        if not bajo < nuevo < alto:
            nuevo = 0.5 * (bajo + alto)     # paso de bisección de respaldo
        alfa = nuevo
    return alfa, MAX_ITERACIONES


def angulo_compensado(u, metodo="newton", tol=TOLERANCIA):
    """Ángulo que entrega exactamente la fracción ``u`` con el método elegido."""
    if metodo == "newton":
        return angulo_por_newton(u, tol)
    if metodo == "biseccion":
        return angulo_por_biseccion(u, tol)
    raise ValueError(f"método de inversión desconocido: {metodo!r}")


def disparo_real(alfa, alfa_min, alfa_max, resolucion=0.0, dispersion=0.0, rng=None):
    """Lo que hace un circuito de disparo real con el ángulo pedido.

    En los extremos del medio ciclo el triac no puede regular:

    - Más tarde que ``alfa_max`` (cerca de 180°) el medio ciclo se está
      acabando: la corriente no alcanza la de mantenimiento y el triac no
      conduce. Queda APAGADO (180°, 0 % de potencia).
    - Antes que ``alfa_min`` (cerca de 0°) apenas hay voltaje para cebarlo.
      Los controladores dejan entonces la compuerta activa todo el ciclo:
      CONDUCCIÓN COMPLETA (0°, 100 % de potencia).

    Entre los dos límites:

    - ``dispersion`` (grados, desviación típica): el disparo no es exacto.
    - ``resolucion`` (grados): el temporizador solo da ángulos múltiplos de ella.

    Si la dispersión lleva el disparo más allá de ``alfa_max``, ese medio
    ciclo el triac no conduce; si lo adelanta antes de ``alfa_min``, dispara
    en ``alfa_min``.
    """
    if alfa > alfa_max:
        return ALFA_APAGADO
    if alfa < alfa_min:
        return 0.0
    if dispersion > 0.0 and rng is not None:
        alfa += rng.gauss(0.0, dispersion)
    if resolucion > 0.0:
        alfa = round(alfa / resolucion) * resolucion
    if alfa > alfa_max:
        return ALFA_APAGADO
    return max(alfa, alfa_min)


# ======================================================================
# El actuador completo
# ======================================================================
class Triac:
    """Convierte la señal de control u en la fracción de potencia que llega al horno.

    ``parametros`` es un ``ParametrosActuador`` (se lee en cada paso).
    ``aplicar`` devuelve ``(fracción, α, iteraciones)``; en modo ideal la
    fracción es exactamente u (los resultados no cambian) y α es NaN.
    """

    def __init__(self, parametros):
        self.parametros = parametros

    def aplicar(self, u, rng=None):
        p = self.parametros
        if p.modo == "ideal":
            return u, math.nan, 0
        if u <= 0.0:
            return 0.0, ALFA_APAGADO, 0
        if p.modo == "triac_lineal":
            alfa, iteraciones = angulo_lineal(u), 0
        elif p.modo == "triac_compensado":
            alfa, iteraciones = angulo_compensado(u, p.metodo)
        else:
            raise ValueError(f"modo de actuador desconocido: {p.modo!r}")
        alfa = disparo_real(alfa, p.alfa_min, p.alfa_max, p.resolucion, p.dispersion, rng)
        return fraccion_potencia(alfa), alfa, iteraciones


def energia_kwh(joules):
    return joules / 3.6e6


# ======================================================================
# Formas de onda (osciloscopio)
# ======================================================================
ANCHO_PULSO = 2.0       # grados eléctricos del pulso de compuerta (~93 µs a 60 Hz)
_EPS_FASE = 1e-7        # tolerancia del redondeo al reducir el ángulo al medio ciclo (360 + 64,65 → 64,6499…)
V_COMPUERTA = 5.0       # V del pulso de compuerta


def tiempo_disparo_ms(alfa, frecuencia):
    """Milisegundos desde el cruce por cero hasta el disparo: α/360 de un periodo."""
    return alfa / 360.0 / frecuencia * 1000.0


def _conduce(fase, alfa):
    """¿Conduce el triac en ese punto del medio ciclo (``fase`` en [0, 180))?"""
    if alfa <= 0.0:
        return True                 # compuerta activa todo el ciclo: conducción completa
    if alfa >= ALFA_APAGADO:
        return False                # sin disparo
    return fase >= alfa - _EPS_FASE


def _compuerta(fase, alfa, ancho):
    if alfa <= 0.0:
        return V_COMPUERTA          # compuerta activa todo el tiempo
    if alfa >= ALFA_APAGADO:
        return 0.0
    return V_COMPUERTA if alfa - _EPS_FASE <= fase < alfa + ancho else 0.0


def formas_de_onda(alfa, V_red, R, frecuencia=60.0, ciclos=2, resolucion=0.25, ancho_pulso=ANCHO_PULSO):
    """Señales de un osciloscopio sobre la carga resistiva del horno.

    Para ``ciclos`` ciclos de la red, muestreados cada ``resolucion`` grados
    eléctricos (más un punto justo antes y otro justo en cada disparo, para
    que el salto de la onda quede vertical), devuelve un dict de listas:

    - ``t_ms``, ``angulo``      : tiempo (ms) y ángulo eléctrico (grados, 0 a 360·ciclos);
    - ``v_red``                 : V_pico·sen(ángulo), con V_pico = V_red·raíz(2);
    - ``v_carga``               : la onda recortada: igual a la red mientras el
                                  triac conduce (desde α hasta el cruce por cero), 0 si no;
    - ``corriente``             : v_carga / R (carga resistiva: en fase con el voltaje);
    - ``potencia``              : v_carga · corriente (siempre ≥ 0);
    - ``v_triac``               : v_red − v_carga (lo que aguanta el triac apagado);
    - ``compuerta``             : el pulso de disparo en cada medio ciclo.
    """
    V_pico = V_red * math.sqrt(2.0)
    total = 360.0 * ciclos
    angulos = [i * resolucion for i in range(int(round(total / resolucion)) + 1)]
    if 0.0 < alfa < ALFA_APAGADO:
        for medio in range(2 * ciclos):
            disparo = medio * 180.0 + alfa
            angulos += [disparo - 1e-6, disparo]
    angulos = sorted(set(a for a in angulos if 0.0 <= a <= total))
    ondas = {k: [] for k in ("t_ms", "angulo", "v_red", "v_carga", "corriente", "potencia", "v_triac", "compuerta")}
    for a in angulos:
        fase = a % 180.0
        if a == total:
            fase = 180.0            # el último punto cierra el medio ciclo (cruce por cero)
        v = V_pico * math.sin(math.radians(a))
        vc = v if _conduce(fase, alfa) else 0.0
        i = vc / R
        ondas["t_ms"].append(a / 360.0 / frecuencia * 1000.0)
        ondas["angulo"].append(a)
        ondas["v_red"].append(v)
        ondas["v_carga"].append(vc)
        ondas["corriente"].append(i)
        ondas["potencia"].append(vc * i)
        ondas["v_triac"].append(v - vc)
        ondas["compuerta"].append(_compuerta(fase, alfa, ancho_pulso))
    return ondas


def _promedio(t, y):
    """Promedio temporal por la regla del trapecio: (1/T)·∫ y dt."""
    area = sum(0.5 * (y[k] + y[k - 1]) * (t[k] - t[k - 1]) for k in range(1, len(t)))
    return area / (t[-1] - t[0])


def medidas(ondas):
    """Lo que mediría un osciloscopio, integrando las ondas con la regla del trapecio.

    Devuelve ``V_rms_carga``, ``I_rms`` y ``P_media`` (W). La potencia media
    debe coincidir con la fórmula del triac: es la comprobación numérica.
    """
    t = ondas["t_ms"]
    return {
        "V_rms_carga": math.sqrt(_promedio(t, [v * v for v in ondas["v_carga"]])),
        "I_rms": math.sqrt(_promedio(t, [i * i for i in ondas["corriente"]])),
        "P_media": _promedio(t, ondas["potencia"]),
    }
