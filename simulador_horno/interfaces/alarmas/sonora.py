"""Alarma sonora para el impulso de perturbación.

Usa ``winsound`` (disponible solo en Windows); en otras plataformas la
alarma simplemente se omite.
"""


def alarma_impulso(hay_impulso):
    if not hay_impulso:
        return
    try:
        import winsound
        winsound.Beep(1000, 300)  # 1000 Hz durante 300 ms
    except (ImportError, RuntimeError):
        pass  # plataforma sin soporte de winsound
