"""No regresión: corridas de referencia con semilla fija.

Se generaron ANTES de encapsular el estado (Fase 1 de la versión
Streamlit) y se guardan en ``tests/referencias/<escenario>.json``. Cada
archivo tiene la huella SHA-256 de las series ``(t, T, error, u)`` del
historial y algunos valores sueltos para diagnosticar si la huella cambia.

- Sin perturbaciones las series deben coincidir BIT A BIT en cualquier
  sistema: es aritmética IEEE pura.
- Con perturbaciones (semilla fija) también coinciden bit a bit en el
  sistema donde se generaron (Windows). En otro sistema (Linux, en GitHub
  Actions) ``sin``, ``exp`` y ``gauss`` salen de otra biblioteca matemática y
  pueden diferir en el último bit; entonces se exige que los contadores sean
  idénticos y que los valores y estadísticas de las series coincidan con
  tolerancia relativa 1e-9.

Solo ``correr`` depende de la API del simulador: al refactorizar se adapta
esa función y los archivos de referencia NO se tocan.

Regenerar (solo si un cambio de resultados es intencional):

    set REGENERAR_REFERENCIAS=1 && python -m pytest tests/test_no_regresion.py
"""
import hashlib
import json
import os
from array import array
from pathlib import Path

import pytest

from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import Configuracion
from simulador_horno.simulacion.simulador import Simulador

CARPETA = Path(__file__).parent / "referencias"
PERTURBACIONES = tuple(a for a, _, _ in limites.PERTURBACIONES)

# nombre -> (horas simuladas, semilla, cambios sobre los valores por defecto)
ESCENARIOS = {
    "euler_defecto": (2, None, {}),
    "heun_defecto": (1, None, {"metodo": "heun"}),
    "rk4_defecto": (1, None, {"metodo": "rk4"}),
    "sin_anti_windup": (2, None, {"anti_windup": "ninguno"}),
    "recorte_ki_bajo": (2, None, {"anti_windup": "recorte", "KI": 2}),
    "arranque_caliente": (1, None, {"T_INICIAL": 1100.0}),
    "medicion_perturbada": (2, 2026, {"error_oscilante": True, "flag_error": True,
                                      "ruido_termopar": True}),
    "horno_perturbado": (2, 2026, {"puerta": True, "red_variable": True,
                                   "ambiente_variable": True}),
    "todas_perturbaciones": (2, 7, {a: True for a in PERTURBACIONES}),
}


def correr(horas, semilla, cambios):
    """Ejecuta un escenario y devuelve el simulador al terminar."""
    config = Configuracion()
    partes = (config.simulacion, config.pid, config.perturbaciones, config.horno)
    for clave, valor in cambios.items():
        for parte in partes:
            if hasattr(parte, clave):
                setattr(parte, clave, valor)
                break
        else:
            raise KeyError(clave)
    sim = Simulador(config, semilla=semilla)
    sim.avanzar(round(horas * 3600 / config.horno.DT))
    return sim


def huella(historial):
    h = hashlib.sha256()
    for serie in (historial.tiempos, historial.temperaturas, historial.errores, historial.potencias):
        h.update(array("d", serie).tobytes())
    return h.hexdigest()


TOLERANCIA = 1e-9
_SERIES = ("tiempos", "temperaturas", "errores", "potencias")


def estadisticas(serie):
    """Suma, suma de valores absolutos, extremos y 20 muestras repartidas."""
    paso = max(1, len(serie) // 20)
    return {"suma": sum(serie), "suma_abs": sum(abs(x) for x in serie),
            "min": min(serie), "max": max(serie), "muestras": serie[::paso][:20]}


def resumen(motor):
    h = motor.historial
    m = motor.metricas()
    return {
        "sha256": huella(h),
        "series": {nombre: estadisticas(getattr(h, nombre)) for nombre in _SERIES},
        "muestras": len(h.tiempos),
        "t_final": motor.t,
        "T_final": motor.T,
        "u_final": motor.u,
        "error_final": motor.error,
        "impulsos": motor.impulsos,
        "aperturas": motor.aperturas,
        "metricas": vars(m),
    }


@pytest.mark.parametrize("nombre", ESCENARIOS)
def test_corrida_igual_a_la_referencia(nombre):
    obtenido = resumen(correr(*ESCENARIOS[nombre]))
    ruta = CARPETA / f"{nombre}.json"
    if os.environ.get("REGENERAR_REFERENCIAS"):
        CARPETA.mkdir(exist_ok=True)
        ruta.write_text(json.dumps(obtenido, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pytest.skip("referencia regenerada")
    esperado = json.loads(ruta.read_text(encoding="utf-8"))
    for clave in ("muestras", "impulsos", "aperturas"):   # contadores: siempre exactos
        assert obtenido[clave] == esperado[clave], clave
    semilla = ESCENARIOS[nombre][1]
    if obtenido["sha256"] == esperado["sha256"] or semilla is None:
        # bit a bit (sin azar, en cualquier sistema); primero lo legible
        for clave in ("t_final", "T_final", "u_final", "error_final", "metricas", "series"):
            assert obtenido[clave] == esperado[clave], clave
        assert obtenido["sha256"] == esperado["sha256"]
        return
    # con perturbaciones en otro sistema: misma corrida salvo el último bit de libm
    for clave in ("t_final", "T_final", "u_final", "error_final"):
        assert _cerca(obtenido[clave], esperado[clave]), clave
    for clave, valor in esperado["metricas"].items():
        assert _cerca(obtenido["metricas"][clave], valor), clave
    for nombre_serie in _SERIES:
        e, o = esperado["series"][nombre_serie], obtenido["series"][nombre_serie]
        for k in ("suma", "suma_abs", "min", "max"):
            assert _cerca(o[k], e[k]), (nombre_serie, k)
        assert all(_cerca(a, b) for a, b in zip(o["muestras"], e["muestras"], strict=True)), nombre_serie


def _cerca(obtenido, esperado):
    if obtenido is None or esperado is None:
        return obtenido is esperado
    return obtenido == pytest.approx(esperado, rel=TOLERANCIA, abs=TOLERANCIA)
