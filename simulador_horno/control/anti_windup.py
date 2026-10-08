"""Anti-windup: evita que el término integral del PID crezca en exceso.

Mientras el actuador está saturado (horno al 100 % durante la subida) el
error sigue acumulándose en la integral aunque la potencia ya no pueda
aumentar. Al llegar al setpoint esa integral "inflada" mantiene la
potencia alta y la temperatura se pasa mucho (windup).

Modos (``parametros_pid.anti_windup``, opción 5 del menú):

- ``"ninguno"``     : integra siempre. Sirve para mostrar el problema.
- ``"recorte"``     : el método original del simulador. Si la integral
                      supera ``limites.UMBRAL_INTEGRAL`` se multiplica por
                      ``parametros_pid.restringir_integral``. Con KI bajo el
                      tope fijo impide alcanzar el equilibrio (error permanente).
- ``"condicional"`` : integración condicional (clamping), el estándar
                      industrial. No integra mientras la salida está
                      saturada y el error empuja en ese mismo sentido.
"""
from simulador_horno.configuracion import limites
from simulador_horno.configuracion import parametros_pid as vpid

NOMBRES = {
    "ninguno": "Ninguno",
    "recorte": "Recorte de la integral",
    "condicional": "Integración condicional",
}


def minimizar_integral(integral):
    r = vpid.restringir_integral
    return max(min(integral, integral * r), -integral * r)


def limitar(modo, integral_previa, integral_nueva, error, u_bruta):
    """Integral que se conserva en este paso según el ``modo``.

    ``u_bruta`` es la salida normalizada (u / U_MAX) calculada con
    ``integral_nueva``, antes de saturar a [0, 1].
    """
    if modo == "ninguno":
        return integral_nueva
    if modo == "recorte":
        if integral_nueva > limites.UMBRAL_INTEGRAL:
            return minimizar_integral(integral_nueva)
        return integral_nueva
    if modo == "condicional":
        satura_arriba = u_bruta > 1.0 and error > 0
        satura_abajo = u_bruta < 0.0 and error < 0
        return integral_previa if (satura_arriba or satura_abajo) else integral_nueva
    raise ValueError(f"modo de anti-windup desconocido: {modo!r}")
