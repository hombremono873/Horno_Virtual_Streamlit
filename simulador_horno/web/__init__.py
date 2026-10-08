"""Interfaz web (Streamlit + Plotly).

- ``datos``     : diezmado para dibujar y tabla/CSV de descarga (pandas).
- ``graficas``  : plantilla de Plotly a partir de ``estilos.tema`` y figura del monitor.
- ``ejecucion`` : avance del modo "en vivo" según la velocidad elegida.
- ``app``       : la página de Streamlit (barra lateral, monitor, resultados).

El núcleo (``simulacion``, ``control``...) NO importa este paquete.
"""
