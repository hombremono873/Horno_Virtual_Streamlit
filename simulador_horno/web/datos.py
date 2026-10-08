"""Datos de la corrida para la web: diezmado y CSV de descarga."""
import math
from datetime import datetime

import pandas as pd

MAX_PUNTOS = 2000   # puntos por curva que se envían al navegador

COLUMNAS_CSV = ("t_s", "T", "T_set", "error", "u", "P", "I", "D", "perturbacion", "T_medida")
_DECIMALES = {"t_s": 1, "T": 4, "T_set": 4, "error": 4, "u": 5, "P": 5, "I": 5, "D": 5,
              "perturbacion": 4, "T_medida": 4}


def indices_diezmados(n, maximo=MAX_PUNTOS):
    """Índices de a lo sumo ~``maximo`` muestras repartidas; siempre incluye la última."""
    if n <= maximo:
        return range(n)
    paso = math.ceil(n / maximo)
    indices = list(range(0, n, paso))
    if indices[-1] != n - 1:
        indices.append(n - 1)
    return indices


def indices_ventana(tiempos, muestras, intervalo, maximo=MAX_PUNTOS):
    """Índices de las últimas ``muestras`` muestras, diezmados de forma ESTABLE.

    Con la ventana deslizándose, elegir "una de cada k" por posición haría
    que en cada refresco se dibujaran muestras distintas y la curva temblara.
    Por eso se eligen por su número de muestra absoluto (``t / intervalo``):
    una muestra que se dibujó se sigue dibujando mientras esté en la ventana.
    Siempre incluye la última.
    """
    n = len(tiempos)
    inicio = max(0, n - muestras)
    paso = max(1, math.ceil(muestras / maximo))
    indices = [i for i in range(inicio, n) if round(tiempos[i] / intervalo) % paso == 0]
    if n and (not indices or indices[-1] != n - 1):
        indices.append(n - 1)
    return indices


def diezmar(serie, indices):
    return [serie[i] for i in indices]


def tabla(historial):
    """La corrida completa (sin diezmar) como DataFrame con las columnas del CSV.

    - ``perturbacion``: lo que las perturbaciones de la medición sumaron al
      error (error visto − error real).
    - ``T_medida``: la temperatura que leyó el controlador (T_set − error).
    """
    h = historial
    df = pd.DataFrame({
        "t_s": h.tiempos,
        "T": h.temperaturas,
        "T_set": h.setpoints,
        "error": h.errores,
        "u": h.potencias,
        "P": h.proporcionales,
        "I": h.integrales,
        "D": h.derivativos,
    })
    df["perturbacion"] = df["error"] - (df["T_set"] - df["T"])
    df["T_medida"] = df["T_set"] - df["error"]
    return df[list(COLUMNAS_CSV)]


def csv(historial):
    """CSV estándar (separador "," y punto decimal), en UTF-8."""
    return tabla(historial).round(_DECIMALES).to_csv(index=False).encode("utf-8")


def nombre_csv(simulador, fecha=None):
    fecha = fecha or datetime.now()
    pid = simulador.config.pid
    return f"horno_{fecha:%Y-%m-%d_%H%M%S}_{simulador.metodo}_dt{simulador.config.horno.DT:g}_{pid.anti_windup}.csv"
