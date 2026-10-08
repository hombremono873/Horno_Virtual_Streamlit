# Simulador de Horno Eléctrico con Control PID (versión web)

[![Pruebas](https://github.com/hombremono873/Horno_Virtual_Streamlit/actions/workflows/pruebas.yml/badge.svg)](https://github.com/hombremono873/Horno_Virtual_Streamlit/actions/workflows/pruebas.yml)

**Universidad de Antioquia – Facultad de Ingeniería**  
**Autor:** Omar Alberto Torres  
**Docente:** Yony Ceballos  
**Fecha:** 2025–2026  

---

## Contexto del proyecto

Este trabajo implementa un **simulador computacional de un horno eléctrico con regulación PID**. Integra conceptos de **transferencia de calor, modelado matemático y control de procesos** con los **métodos numéricos** estudiados en la asignatura de Métodos Numéricos.

El simulador permite analizar de forma numérica y visual el comportamiento dinámico del horno, comparar métodos de integración, estudiar su estabilidad y explorar la robustez del controlador PID frente a perturbaciones.

Esta es la **versión web**, pensada para usarse desde el navegador sin instalar nada. La versión de escritorio (menú de consola, monitor gráfico y `main.exe`) está en el repositorio [Hornovirtual_2026](https://github.com/hombremono873/Hornovirtual_2026).

---

## Inicio rápido

1. Abre la aplicación en el navegador (o ejecútala en tu computador, ver [Instalación](#instalación-y-desarrollo)).
2. La app arranca en modo **En vivo** a **x60** (1 segundo real = 1 minuto simulado). Pulsa **▶ Iniciar** en la barra lateral y mira calentarse el horno.
3. El monitor es un solo lienzo, como el de un tablero de control: arriba los indicadores; a la izquierda la temperatura (con el setpoint), el error y la potencia u; a la derecha las **paredes del horno**, que se iluminan con su temperatura; abajo la **evolución del color**.
4. El eje de temperatura está **centrado en el setpoint** (y el del error en 0): durante la subida la escala es amplia y, al estabilizarse, se cierra hasta ±5 °C para que se vea cómo oscila el horno alrededor de la referencia.
5. Cuando pasan unos 83 min simulados (5000 muestras), la gráfica empieza a **correrse de derecha a izquierda**: entra lo nuevo y sale lo más viejo.
6. Los valores (temperatura, error, aportes P, I y D, métricas…) están en la pestaña **🔢 Indicadores**; al terminar ahí aparecen el desempeño y el botón **⬇ Descargar la corrida (CSV)**. Cambiar de pestaña no detiene la corrida.
7. Para comparar sintonías usa el modo **Corrida completa** y **▶ Simular**: la corrida se hace en un instante y la anterior queda superpuesta en gris punteado.

## La barra lateral

| Sección | Qué contiene |
|---|---|
| **Modo** | *En vivo* (por defecto: se ve avanzar, con ▶ Iniciar / ⏸ Pausar y ↺ Reiniciar) o *Corrida completa* (toda la duración de una vez, para comparar) |
| **Horno** | T ambiente, setpoint, T máx. de equilibrio, **T inicial** (arranque en frío o en caliente) y τ. Muestra **B** calculado |
| **Controlador PID** | Kp, Ki, Kd, anti-windup (ninguno, recorte, **integración condicional**) y el factor de recorte |
| **Perturbaciones** | 3 sobre la **medición** y 3 sobre el **horno real** (ver [Modelo y control](#modelo-y-control)) y los impulsos por hora |
| **Simulación** | Duración (30 min a 8 h; *sin límite* solo en vivo), velocidad (en vivo), método numérico, Δt y **semilla** |

**En vivo** se pueden cambiar el setpoint, las ganancias y las perturbaciones a mitad de la corrida y ver cómo reacciona el controlador. El método numérico, la T inicial y la duración se aplican al **reiniciar**. Cuando ocurre un impulso en la medición aparece un aviso ⚡.

---

## Experimentos sugeridos

| Experimento | Cómo | Qué se observa |
|---|---|---|
| **Windup** | Anti-windup *Ninguno* y luego *Integración condicional* | Sin anti-windup el horno se pasa ~280 °C; con él llega limpio a 1000 °C |
| **Límite del recorte** | Ki = 2 con anti-windup *Recorte* y luego con *Integración condicional* | Con recorte el horno no llega al setpoint; con integración condicional sí |
| **Orden de los métodos** | Comparar con la solución exacta | Orden observado ≈ 1 (Euler), 2 (Heun) y 4 (RK4) |
| **Estabilidad numérica** | Estabilidad con Δt grande | Con Δt > 2τ Euler diverge aunque la física sea estable |
| **Métodos en la simulación** | Δt = 30 s con Euler y luego con RK4 | Euler se aparta de RK4 con pasos grandes |
| **Arranque en caliente** | T inicial = 600 (o 1200) | Llega antes; desde 1200 °C el PID apaga la potencia y el horno se enfría |
| **Puerta abierta** | Perturbación *Apertura de puerta* | Caídas de hasta ~50 °C en régimen y la recuperación del PID |
| **Red eléctrica** | Perturbación *Fluctuación de la red* | La temperatura oscila ±3 °C alrededor del setpoint |
| **Sensor vs. realidad** | Perturbación *Ruido del termopar* | El controlador lee ±1 °C de ruido, pero el horno apenas se mueve |

Para comparar dos corridas, cambia **una sola cosa** a la vez y usa la **misma duración**. Con perturbaciones, usa la **misma semilla** para que el azar sea idéntico en ambas y la diferencia se deba solo a lo que cambiaste.

---

## Velocidad y duración

El horno real tarda más de una hora en llegar a 1000 °C. La **velocidad** comprime el tiempo de **ejecución**, no la física: con x60 cada segundo real equivale a un minuto simulado. El paso `Δt` y los resultados son los mismos a cualquier velocidad.

La **duración** son las horas **simuladas** tras las que la corrida se detiene sola. Con la configuración por defecto el horno llega al setpoint hacia el minuto 74, así que **2 h** muestran la subida, la llegada y la estabilización.

---

## Método numérico

Elige con qué método se resuelve en cada paso la ecuación del horno, `dT/dt = (T_AMB − T)/τ + B·u`:

| Método | Orden | Evaluaciones de dT/dt por paso | Estable si |
|--------|-------|-------------------------------|------------|
| Euler | 1 | 1 | Δt < 2τ |
| Heun (RK2) | 2 | 2 | Δt < 2τ |
| Runge-Kutta 4 | 4 | 4 | Δt < ~2,785τ |

Un método de orden p reduce su error unas 2^p veces al dividir Δt a la mitad. Con el Δt por defecto (0,1 s) las curvas son casi idénticas.

- **Comparar con la solución exacta:** integra a potencia plena con Δt = 240, 120, 60, 30 y 15 s y compara con `T(t) = T_eq + (T0 − T_eq)·e^(−t/τ)`. Da los errores y los órdenes observados, y el costo frente a la precisión.
- **Estabilidad con Δt grande:** con la potencia apagada, cada método multiplica la desviación (T − T_AMB) por un factor R en cada paso. Con |R| > 1 diverge; por ejemplo, Euler con Δt = 2,5τ predice −7336 °C. **Solo Euler oscila**: Heun y RK4 tienen R > 0 y, cuando fallan, divergen sin oscilar.

---

## Métricas de desempeño

Se calculan sobre la **temperatura real** del horno:

| Métrica | Significado |
|---|---|
| **Sobrepaso** | Cuánto se pasa del setpoint, en °C y en % del salto. Si el horno arranca por encima del setpoint, se mide por debajo |
| **Tiempo de subida** | Tiempo entre el 10 % y el 90 % del salto |
| **Tiempo al 90 %** | Cuándo recorre el 90 % del salto |
| **Establecimiento** | Desde cuándo la temperatura queda siempre dentro de ±1 % del salto |
| **Error final** | Setpoint − temperatura al terminar |
| **IAE** = ∫\|e\| dt | Integral del error absoluto, en °C·min: el **área entre la curva y el setpoint**. Premia que el error sea pequeño todo el tiempo |
| **ISE** = ∫e² dt | Integral del error al cuadrado, en °C²·min: **castiga mucho los errores grandes**, como sobrepasos fuertes o subidas lentas |

Para IAE e ISE, **menor es mejor**, y solo son comparables entre corridas de la **misma duración**. En este horno casi todo su valor viene de la subida inicial, limitada por la física; las diferencias aparecen cuando algo va mal (por ejemplo, sin anti-windup el IAE sube ~19 %).

---

## Modelo y control

- **Modelo térmico:** sistema de **primer orden**, con pérdidas al ambiente según la **Ley de Enfriamiento de Newton** más la potencia del calentador:
  `dT/dt = (T_AMB − T)/τ + B·u`, con `u ∈ [0, 1]` (un horno no enfría activamente).
  La ganancia `B = (T_MAX_EQ − T_AMB)/τ` se deriva de la temperatura de equilibrio a potencia plena (1300 °C por defecto), lo que da un calentamiento máximo realista de ~0,42 °C/s.
- **PID** (por defecto Kp = 200, Ki = 10, Kd = 2):
  - **Proporcional:** responde al error instantáneo.
  - **Integral:** corrige el error acumulado (regla del trapecio), protegida por el **anti-windup** (por defecto, **integración condicional**).
  - **Derivativa:** se calcula sobre la **temperatura medida**, para evitar picos cuando el error salta.
- **Fallos y perturbaciones**, todas apagadas por defecto:

  | Sobre la **medición** (el controlador lee mal) | Sobre el **horno real** (cambia la física) |
  |---|---|
  | Error oscilante: senoide de 20 °C + ruido | Apertura de puerta: ~2 por hora, 90 s, las pérdidas se triplican |
  | Impulsos en el error: ±80 °C, ~6 por hora | Fluctuación de la red: voltaje ±6 % → potencia ±12 % (P ∝ V²) |
  | Ruido del termopar: ±1 °C gaussiano | Ambiente variable: ±10 °C en 1 h (el PID lo compensa casi por completo) |

  Con las del horno, la temperatura sigue moviéndose alrededor del setpoint como en un horno real. Las tres actúan dentro de la misma ecuación `dT/dt`, sea cual sea el método numérico.
- **Semilla:** el azar de las perturbaciones sale de un generador propio de cada simulación. Con la misma semilla y la misma configuración, la corrida se repite exactamente; sin semilla, cada corrida es distinta.

---

## Resultados en archivo

El botón **⬇ Descargar la corrida (CSV)** entrega un archivo estándar (separador `,` y punto decimal) con una fila por segundo simulado:

| Columna | Significado |
|---|---|
| `t_s` | tiempo simulado (s) |
| `T` | temperatura **real** del horno (°C) |
| `T_set` | setpoint en ese instante (°C) |
| `error` | el error que vio el controlador, incluidas las perturbaciones de la medición (°C) |
| `u` | señal de control, de 0 a 1 |
| `P`, `I`, `D` | aporte de cada término del PID; `P + I + D` es u antes de saturar a [0, 1] |
| `perturbacion` | lo que las perturbaciones de la medición sumaron al error (°C) |
| `T_medida` | la temperatura que leyó el controlador, `T_set − error` (°C) |

Para abrirlo en Excel en español: *Datos → Desde texto/CSV* y elige el delimitador **coma**.

---

## Instalación y desarrollo

Requiere Python 3.13. El monitor carga la biblioteca de gráficas (Plotly.js) desde internet, así que el navegador necesita conexión.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt                          # la app web
pip install -r requirements.txt -r requirements-dev.txt  # + pytest
streamlit run streamlit_app.py                           # abre la app en http://localhost:8501
python -m pytest                                         # pruebas automáticas (también en GitHub Actions)
```

Para detener la app, pulsa `Ctrl+C` en la terminal.

**En Windows lo más simple es `iniciar_web.bat`** (doble clic, o escríbelo en una terminal dentro de `simulador`). Siempre usa el `.venv` de este proyecto, aunque en la terminal haya otro entorno activo; un `python -m streamlit ...` con otro entorno activo falla con *No module named streamlit*. La versión de escritorio se ejecuta desde su propio repositorio, [Hornovirtual_2026](https://github.com/hombremono873/Hornovirtual_2026) (`dist\main.exe` o `python main.py`).

## Publicar en Streamlit Community Cloud

1. Sube este repositorio a GitHub (público, o privado con acceso de Streamlit).
2. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub y pulsa **Create app**.
3. Elige el repositorio, la rama `main` y el archivo principal **`streamlit_app.py`**.
4. En **Advanced settings** elige **Python 3.13**.
5. Pulsa **Deploy**. Streamlit instala `requirements.txt` y aplica el tema de `.streamlit/config.toml`. Cada `git push` a `main` actualiza la app.

Cada estudiante que abre el enlace tiene su propia simulación: lo que cambia uno no afecta a los demás.

## Estructura del proyecto

```text
simulador/
├── streamlit_app.py            # punto de entrada de la app web
├── .streamlit/config.toml      # tema de la app
├── requirements*.txt           # dependencias (app web / desarrollo)
├── CLAUDE.md  README.md        # guía técnica · esta guía
├── pytest.ini  tests/          # pruebas automáticas (tests/referencias: corridas de no regresión)
├── documentos/                 # traspaso y plan de la versión web
└── simulador_horno/
    ├── configuracion/          # ¿con qué parámetros?   Configuracion (horno, PID, perturbaciones, simulación), límites
    ├── modelo/                 # ¿qué se simula?        horno, perturbaciones, actuador
    ├── control/                # ¿quién controla?       PID, anti-windup, saturación, error
    ├── numerico/               # ¿con qué método?       integradores, comparación, estabilidad
    ├── simulacion/             # ¿quién coordina?       Simulador, reloj, historial, métricas, resultados
    ├── web/                    # ¿qué ve el usuario?    página Streamlit, gráficas Plotly, CSV, modo en vivo
    └── estilos/                # ¿cómo se ve?           paleta de las gráficas
```

---

## Contacto

**Omar Alberto Torres**  
**Tel:** [+57 304 344 0112](tel:+573043440112)  
**Correo:** [omara.torres@udea.edu.co](mailto:omara.torres@udea.edu.co)

> Si necesitan información adicional sobre la ejecución o detalles técnicos del proyecto, escríbanme al correo institucional. También pueden revisar los comentarios del código fuente para aclaraciones rápidas.
