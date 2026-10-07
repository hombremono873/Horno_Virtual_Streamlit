"""Alarma sonora para el impulso de perturbación.

Usa ``winsound`` (disponible solo en Windows); en otras plataformas la
alarma simplemente se omite.

El pitido corre en un hilo aparte para no congelar la simulación (a
velocidades altas el bucle no puede esperar 300 ms). Si aún está sonando
el anterior, el nuevo se descarta.
"""
import threading

_hilo = None


def _pitar():
    try:
        import winsound
        winsound.Beep(1000, 300)  # 1000 Hz durante 300 ms
    except (ImportError, RuntimeError):
        pass  # plataforma sin soporte de winsound


def alarma_impulso(hay_impulso):
    global _hilo
    if not hay_impulso:
        return
    if _hilo is not None and _hilo.is_alive():
        return
    _hilo = threading.Thread(target=_pitar, daemon=True)
    _hilo.start()
