"""Guardado de cada corrida en un archivo CSV (y su lectura).

Un archivo por corrida en la carpeta ``limites.CARPETA_RESULTADOS``, junto
al ejecutable o, desde el código, en la carpeta de trabajo (``simulador/``):

    resultados/2026-10-08_143015_rk4_dt0,1_condicional.csv

Formato (separador y decimal de ``limites``; UTF-8 con BOM para Excel):

    # parámetro;valor          <- configuración y métricas de la corrida
    # metodo;rk4
    # ...
    t_s;T_C;T_set_C;error_C;u   <- una fila por segundo simulado
    0,0;30,0000;1000,0000;970,0000;1,00000

``error_C`` es el error que vio el controlador (con perturbaciones, si
estaban activas); la temperatura real es ``T_C``.

Este módulo hace E/S de archivos pero no importa rich ni Qt.
"""
import sys
from datetime import datetime
from pathlib import Path

from simulador_horno.configuracion import limites

COLUMNAS = ("t_s", "T_C", "T_set_C", "error_C", "u")
_FORMATOS = (".1f", ".4f", ".4f", ".4f", ".5f")


def carpeta_resultados():
    """Junto al ``main.exe`` si está empaquetado; si no, en la carpeta de trabajo."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    return base / limites.CARPETA_RESULTADOS


def _num(valor, formato=".6g"):
    return format(valor, formato).replace(".", limites.CSV_DECIMAL)


def _texto(valor):
    if isinstance(valor, float):
        return _num(valor)
    return "" if valor is None else str(valor)


def nombre_archivo(fecha, metodo, dt, anti_windup):
    return f"{fecha:%Y-%m-%d_%H%M%S}_{metodo}_dt{_num(dt, 'g')}_{anti_windup}.csv"


def guardar(historial, T_set, parametros, metricas=None, carpeta=None, fecha=None):
    """Escribe la corrida y devuelve la ruta del archivo.

    ``parametros``: dict con la configuración (método, Δt, ganancias...);
    debe incluir ``metodo``, ``dt`` y ``anti_windup`` para el nombre.
    """
    fecha = fecha or datetime.now()
    carpeta = Path(carpeta) if carpeta else carpeta_resultados()
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre_archivo(fecha, parametros["metodo"], parametros["dt"], parametros["anti_windup"])

    sep = limites.CSV_SEPARADOR
    lineas = [f"# parámetro{sep}valor", f"# fecha{sep}{fecha:%Y-%m-%d %H:%M:%S}"]
    lineas += [f"# {clave}{sep}{_texto(valor)}" for clave, valor in parametros.items()]
    if metricas is not None:
        for clave, valor in vars(metricas).items():
            lineas.append(f"# metrica_{clave}{sep}{_texto(valor)}")
    lineas.append(sep.join(COLUMNAS))
    for t, T, e, u in zip(historial.tiempos, historial.temperaturas, historial.errores, historial.potencias):
        valores = (t, T, T_set, e, u)
        lineas.append(sep.join(_num(v, f) for v, f in zip(valores, _FORMATOS)))

    # utf-8-sig: el BOM hace que Excel muestre bien °, tildes y ñ
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8-sig")
    return ruta


def leer(ruta):
    """Devuelve ``(parametros, series)``: dict de textos y dict columna -> lista de floats."""
    sep, dec = limites.CSV_SEPARADOR, limites.CSV_DECIMAL
    parametros, series, columnas = {}, {}, None
    for linea in Path(ruta).read_text(encoding="utf-8-sig").splitlines():
        if not linea.strip():
            continue
        if linea.startswith("#"):
            clave, _, valor = linea[1:].strip().partition(sep)
            if clave != "parámetro":
                parametros[clave] = valor
        elif columnas is None:
            columnas = linea.split(sep)
            series = {c: [] for c in columnas}
        else:
            for c, v in zip(columnas, linea.split(sep)):
                series[c].append(float(v.replace(dec, ".")))
    return parametros, series
