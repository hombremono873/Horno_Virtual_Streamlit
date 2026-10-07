"""Configuración común de las pruebas.

La configuración del simulador vive en variables de módulo mutables
(``configuracion/parametros_*``). Este fixture guarda su estado antes de
cada prueba y lo restaura después, para que las pruebas no se contaminen
entre sí. Las listas del historial se restauran EN SITIO porque
``Historial`` guarda referencias a esos mismos objetos.
"""
import types

import pytest

from simulador_horno.configuracion import parametros_horno, parametros_pid, parametros_simulacion
from simulador_horno.modelo.perturbaciones import reiniciar_impulso

_MODULOS = (parametros_horno, parametros_pid, parametros_simulacion)


def _instantanea(modulo):
    return {
        nombre: (valor[:] if isinstance(valor, list) else valor)
        for nombre, valor in vars(modulo).items()
        if not nombre.startswith("__") and not isinstance(valor, (types.FunctionType, types.ModuleType))
    }


@pytest.fixture(autouse=True)
def configuracion_limpia():
    copias = [(m, _instantanea(m)) for m in _MODULOS]
    reiniciar_impulso()
    yield
    for modulo, copia in copias:
        for nombre, valor in copia.items():
            actual = getattr(modulo, nombre)
            if isinstance(actual, list):
                actual[:] = valor
            else:
                setattr(modulo, nombre, valor)
    reiniciar_impulso()
