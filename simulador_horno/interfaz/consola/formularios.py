"""Formularios de configuración: PID, horno, perturbaciones, anti-windup,
velocidad y método numérico.

Cada formulario escribe directamente sobre los módulos de ``configuracion`` para que
el cambio surta efecto en la siguiente simulación. ENTER conserva el valor
actual en cada campo.
"""
from rich.text import Text

from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_horno as horno
from simulador_horno.configuracion import parametros_pid as pid
from simulador_horno.configuracion import parametros_simulacion as sim
from simulador_horno.control.anti_windup import NOMBRES as NOMBRES_ANTI_WINDUP
from simulador_horno.interfaz.consola import marco
from simulador_horno.interfaz.consola.comparacion import resumen_comparacion
from simulador_horno.interfaz.consola.estabilidad import resumen_estabilidad
from simulador_horno.interfaz.graficas.comparacion import VentanaComparacion
from simulador_horno.interfaz.graficas.estabilidad import VentanaEstabilidad
from simulador_horno.numerico.comparacion import DTS_COMPARACION, HORIZONTE, comparar
from simulador_horno.numerico.estabilidad import FRACCIONES_TAU, estudiar
from simulador_horno.numerico.integradores import METODOS, NOMBRES as NOMBRES_METODOS

console = marco.console


# ----------------------------------------------------------------------
# PID (opción 1)
# ----------------------------------------------------------------------
_AYUDA_PID = Text.from_markup(
    "Ganancias del controlador. ENTER conserva el valor actual.\n\n"
    "[b]Kp[/b]  proporcional · responde al error instantáneo\n"
    "[b]Ki[/b]  integral · corrige el error acumulado\n"
    "[b]Kd[/b]  derivativa · amortigua y anticipa"
)


def configurar_pid():
    marco.cabecera_seccion("CONFIGURAR CONTROLADOR PID", _AYUDA_PID, migas=["Configurar PID"])
    pid.KP = marco.pedir_float("Kp", pid.KP)
    pid.KI = marco.pedir_float("Ki", pid.KI)
    pid.KD = marco.pedir_float("Kd", pid.KD)
    marco.resumen("PID actualizado", {"Kp": f"{pid.KP:g}", "Ki": f"{pid.KI:g}", "Kd": f"{pid.KD:g}"})


# ----------------------------------------------------------------------
# Horno (opción 2)
# ----------------------------------------------------------------------
_AYUDA_HORNO = Text.from_markup(
    "Parámetros físicos del horno. ENTER conserva el valor actual.\n\n"
    "[b]T_AMB[/b]     temperatura ambiente (°C)\n"
    "[b]T_SET[/b]     temperatura objetivo (°C)\n"
    "[b]T_MAX_EQ[/b]  temperatura a potencia plena, u = 1 (°C)\n"
    "[b]TAU[/b]       constante de tiempo (s)\n"
    "[b]DT[/b]        paso de integración numérica (s)\n\n"
    "La ganancia térmica B se calcula sola: B = (T_MAX_EQ − T_AMB) / TAU.\n"
    "Para acelerar la corrida usa la opción 6 (velocidad), no DT."
)


def _pedir_mayor(nombre, actual, minimo, motivo):
    """Como ``pedir_float`` pero exige un valor estrictamente mayor que ``minimo``."""
    while True:
        valor = marco.pedir_float(nombre, actual)
        if valor > minimo:
            return valor
        console.print(f"[bold red]  {motivo}[/]")


def configurar_horno():
    marco.cabecera_seccion("CONFIGURAR HORNO", _AYUDA_HORNO, migas=["Configurar horno"])
    horno.T_AMB = marco.pedir_float("T ambiente (T_AMB)", horno.T_AMB)
    horno.T_SET = marco.pedir_float("Setpoint (T_SET)", horno.T_SET)
    horno.T_MAX_EQ = _pedir_mayor("T máx. equilibrio (T_MAX_EQ)", horno.T_MAX_EQ, horno.T_AMB,
                                  "Debe ser mayor que la temperatura ambiente.")
    horno.TAU = _pedir_mayor("Constante de tiempo (TAU)", horno.TAU, 0, "Debe ser mayor que 0.")
    horno.DT = _pedir_mayor("Paso de integración (DT)", horno.DT, 0, "Debe ser mayor que 0.")
    horno.recalcular_B()
    marco.resumen("Horno actualizado", {
        "T_AMB": f"{horno.T_AMB:g} °C",
        "T_SET": f"{horno.T_SET:g} °C",
        "T_MAX_EQ": f"{horno.T_MAX_EQ:g} °C",
        "B (calculada)": f"{horno.B:.4f} °C/s",
        "TAU": f"{horno.TAU:g} s",
        "DT": f"{horno.DT:g} s",
    })


# ----------------------------------------------------------------------
# Perturbaciones (opciones 3 y 4)
# ----------------------------------------------------------------------
def _conmutar(titulo, descripcion, atributo, migas):
    actual = getattr(horno, atributo)
    estado = "[bold green]ACTIVADA[/]" if actual else "[dim]desactivada[/]"
    ayuda = Text.from_markup(f"{descripcion}\n\nEstado actual: {estado}")
    marco.cabecera_seccion(titulo, ayuda, migas=migas)
    nuevo = marco.confirmar("¿Activar esta perturbación?", actual)
    setattr(horno, atributo, nuevo)
    marco.resumen(titulo, {"estado": "activada" if nuevo else "desactivada"})


def configurar_error_oscilante():
    _conmutar(
        "ERROR OSCILANTE",
        "Suma al error una componente senoidal suave más ruido aleatorio.",
        "error_oscilante",
        ["Error oscilante"],
    )


def configurar_error_impulso():
    _conmutar(
        "ERROR DE IMPULSO",
        "Inyecta impulsos térmicos probabilísticos de signo alternante.",
        "flag_error",
        ["Error de impulso"],
    )


# ----------------------------------------------------------------------
# Anti-windup (opción 5)
# ----------------------------------------------------------------------
_DESCRIPCION_ANTI_WINDUP = {
    "ninguno": "La integral crece sin límite: muestra el problema (sobrepaso ~29 %)",
    "recorte": "Método original: recorta la integral sobre un umbral fijo",
    "condicional": "Estándar industrial: no integra mientras la potencia satura",
}

_AYUDA_ANTI_WINDUP = Text.from_markup(
    "Durante la subida el horno va al 100 % y el error se sigue acumulando en\n"
    "la integral aunque la potencia ya no pueda aumentar. Al llegar al setpoint\n"
    "esa integral 'inflada' hace que la temperatura se pase (windup).\n\n"
    "[b]Recorte[/b]: con KI bajo el umbral fijo no deja llegar al setpoint.\n"
    "[b]Integración condicional[/b]: funciona con cualquier sintonía."
)

_AYUDA_RECORTE = Text.from_markup(
    "Factor [0-1] que multiplica la integral cuando supera el umbral.\n\n"
    "1 = sin recorte · valores menores recortan más agresivamente."
)


def configurar_anti_windup():
    claves = list(NOMBRES_ANTI_WINDUP)
    items = [(str(i), NOMBRES_ANTI_WINDUP[c], _DESCRIPCION_ANTI_WINDUP[c]) for i, c in enumerate(claves, 1)]
    items.append((str(len(items) + 1), "Volver", "Conservar el anti-windup actual"))
    eleccion = marco.menu_interactivo(
        "ANTI-WINDUP", items, migas=["Anti-windup"],
        inicial=claves.index(pid.anti_windup) if pid.anti_windup in claves else 0,
    )
    indice = int(eleccion) - 1
    if indice < len(claves):
        pid.anti_windup = claves[indice]

    marco.cabecera_seccion("ANTI-WINDUP", _AYUDA_ANTI_WINDUP, migas=["Anti-windup"])
    filas = {"activo": NOMBRES_ANTI_WINDUP[pid.anti_windup]}
    if pid.anti_windup == "recorte":
        console.print(_AYUDA_RECORTE)
        console.print()
        while True:
            valor = marco.pedir_float("Factor de recorte [0-1]", pid.restringir_integral)
            if 0.0 <= valor <= 1.0:
                pid.restringir_integral = valor
                break
            console.print("[bold red]  El valor debe estar entre 0 y 1.[/]")
        filas["factor de recorte"] = f"{pid.restringir_integral:g}"
    marco.resumen("Anti-windup", filas)


# ----------------------------------------------------------------------
# Velocidad de simulación (opción 6)
# ----------------------------------------------------------------------
_DESCRIPCION_VELOCIDAD = {
    "x1": "Tiempo real · 1 s simulado por segundo",
    "x10": "1 min simulado cada 6 s",
    "x60": "1 min simulado por segundo (recomendada)",
    "x600": "10 min simulados por segundo",
    "máxima": "Sin esperas · tan rápido como permita el equipo",
}

_AYUDA_VELOCIDAD = Text.from_markup(
    "Comprime el tiempo de EJECUCIÓN, no la física: el paso DT y los\n"
    "resultados son los mismos a cualquier velocidad."
)


def configurar_velocidad():
    claves = list(limites.VELOCIDADES)
    items = [(str(i), clave, _DESCRIPCION_VELOCIDAD[clave]) for i, clave in enumerate(claves, 1)]
    items.append((str(len(items) + 1), "Volver", "Conservar la velocidad actual"))
    eleccion = marco.menu_interactivo(
        "VELOCIDAD DE SIMULACIÓN", items, migas=["Velocidad"],
        inicial=claves.index(sim.velocidad) if sim.velocidad in claves else 0,
    )
    indice = int(eleccion) - 1
    if indice < len(claves):
        sim.velocidad = claves[indice]

    marco.cabecera_seccion("VELOCIDAD DE SIMULACIÓN", _AYUDA_VELOCIDAD, migas=["Velocidad"])
    marco.resumen("Velocidad", {"activa": sim.velocidad})


# ----------------------------------------------------------------------
# Método numérico (opción 7)
# ----------------------------------------------------------------------
_DESCRIPCION_METODO = {
    "euler": "Orden 1 · 1 evaluación de dT/dt por paso",
    "heun": "Orden 2 · predictor-corrector, 2 evaluaciones por paso",
    "rk4": "Orden 4 · 4 evaluaciones por paso, el más preciso",
}

_AYUDA_METODO = Text.from_markup(
    "Método con el que se resuelve la ecuación del horno en cada paso Δt:\n\n"
    "    dT/dt = (T_AMB − T)/τ + B·u\n\n"
    "Un método de orden p reduce su error ~2^p veces al dividir Δt a la mitad.\n"
    "Con el Δt por defecto (0,1 s) los tres dan curvas casi idénticas; las\n"
    "diferencias se aprecian al aumentar Δt en la opción 2."
)


def configurar_metodo():
    claves = list(METODOS)
    items = [(str(i), NOMBRES_METODOS[c], _DESCRIPCION_METODO[c]) for i, c in enumerate(claves, 1)]
    clave_comparar = str(len(items) + 1)
    items.append((clave_comparar, "Comparar con la solución exacta",
                  "Error y orden de convergencia de los tres métodos"))
    clave_estabilidad = str(len(items) + 1)
    items.append((clave_estabilidad, "Estabilidad con Δt grande",
                  "Cuándo cada método oscila o diverge"))
    items.append((str(len(items) + 1), "Volver", "Conservar el método actual"))
    eleccion = marco.menu_interactivo(
        "MÉTODO NUMÉRICO", items, migas=["Método numérico"],
        inicial=claves.index(sim.metodo) if sim.metodo in claves else 0,
    )
    if eleccion == clave_comparar:
        comparar_metodos()
        return
    if eleccion == clave_estabilidad:
        estudiar_estabilidad()
        return
    indice = int(eleccion) - 1
    if indice < len(claves):
        sim.metodo = claves[indice]

    marco.cabecera_seccion("MÉTODO NUMÉRICO", _AYUDA_METODO, migas=["Método numérico"])
    marco.resumen("Método numérico", {"activo": NOMBRES_METODOS[sim.metodo]})


_AYUDA_COMPARACION = Text.from_markup(
    "Se integra la ecuación del horno a potencia plena (u = 1) desde T_AMB\n"
    f"durante {HORIZONTE / 60:g} min con cada método y con Δt = "
    f"{', '.join(f'{dt:g}' for dt in DTS_COMPARACION)} s, y se compara\n"
    "con la solución analítica  T(t) = T_eq + (T0 − T_eq)·e^(−t/τ).\n\n"
    "Las gráficas se abren en otra ventana; ciérrala para volver al menú."
)


def comparar_metodos():
    """Compara Euler, Heun y RK4 con la solución exacta: tabla + gráficas."""
    marco.cabecera_seccion("COMPARAR CON LA SOLUCIÓN EXACTA", _AYUDA_COMPARACION,
                           migas=["Método numérico", "Comparar"])
    resultado = comparar()
    console.print(resumen_comparacion(resultado))
    VentanaComparacion(resultado).mostrar_y_esperar()


_AYUDA_ESTABILIDAD = Text.from_markup(
    "Se apaga la potencia (u = 0) y el horno se enfría desde T_SET hacia T_AMB.\n"
    "La física es estable para cualquier Δt, pero los métodos no: con Δt grandes\n"
    "pueden oscilar o divergir. Se prueba con Δt = "
    f"{', '.join(f'{f:g}' for f in FRACCIONES_TAU)} veces τ.\n\n"
    "Las gráficas se abren en otra ventana; ciérrala para volver al menú."
)


def estudiar_estabilidad():
    """Estabilidad de Euler, Heun y RK4 con Δt grandes: tabla + gráficas."""
    marco.cabecera_seccion("ESTABILIDAD CON Δt GRANDE", _AYUDA_ESTABILIDAD,
                           migas=["Método numérico", "Estabilidad"])
    resultado = estudiar()
    console.print(resumen_estabilidad(resultado))
    VentanaEstabilidad(resultado).mostrar_y_esperar()
