"""Anti-windup: evita que el término integral del PID crezca en exceso.

Mientras el actuador está saturado (horno al 100 % durante la subida) el
error sigue acumulándose en la integral aunque la potencia ya no pueda
aumentar. Al llegar al setpoint esa integral "inflada" mantiene la
potencia alta y la temperatura se pasa mucho (windup).

Modos (``ParametrosPID.anti_windup``):

- ``"ninguno"``     : integra siempre. Sirve para mostrar el problema.
- ``"recorte"``     : el método original del simulador. Si la integral
                      supera ``limites.UMBRAL_INTEGRAL`` se multiplica por
                      ``ParametrosPID.restringir_integral``. Con KI bajo el
                      tope fijo impide alcanzar el equilibrio (error permanente).
- ``"condicional"`` : integración condicional (clamping), el estándar
                      industrial. No integra mientras la salida está
                      saturada y el error empuja en ese mismo sentido.
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion.parametros import ParametrosPID

NOMBRES = {
    "ninguno": "Ninguno",
    "recorte": "Recorte de la integral",
    "condicional": "Integración condicional",
}


def minimizar_integral(integral, factor):
    return max(min(integral, integral * factor), -integral * factor)


def limitar(modo, integral_previa, integral_nueva, error, u_bruta,
            factor_recorte=ParametrosPID.restringir_integral):
    """Integral que se conserva en este paso según el ``modo``.

    ``u_bruta`` es la salida normalizada (u / U_MAX) calculada con
    ``integral_nueva``, antes de saturar a [0, 1]. ``factor_recorte`` solo
    se usa en el modo "recorte".
    """
    if modo == "ninguno":
        return integral_nueva
    if modo == "recorte":
        if integral_nueva > limites.UMBRAL_INTEGRAL:
            return minimizar_integral(integral_nueva, factor_recorte)
        return integral_nueva
    if modo == "condicional":
        satura_arriba = u_bruta > 1.0 and error > 0
        satura_abajo = u_bruta < 0.0 and error < 0
        return integral_previa if (satura_arriba or satura_abajo) else integral_nueva
    raise ValueError(f"modo de anti-windup desconocido: {modo!r}")
