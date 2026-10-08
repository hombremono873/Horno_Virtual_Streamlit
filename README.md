# Simulador de Horno Eléctrico con Control PID

[![Pruebas](https://github.com/hombremono873/Hornovirtual_2026/actions/workflows/pruebas.yml/badge.svg)](https://github.com/hombremono873/Hornovirtual_2026/actions/workflows/pruebas.yml)

**Universidad de Antioquia – Facultad de Ingeniería**  
**Autor:** Omar Alberto Torres  
**Docente:** Yony Ceballos  
**Fecha:** 2025  

---

## Contexto del proyecto

Este trabajo implementa un **simulador computacional de un horno eléctrico con regulación PID**. Integra conceptos de **transferencia de calor, modelado matemático y control de procesos** con los **métodos numéricos** estudiados en la asignatura de Métodos Numéricos.

El simulador permite analizar de forma numérica y visual el comportamiento dinámico del horno, comparar métodos de integración, estudiar su estabilidad y explorar la robustez del controlador PID frente a perturbaciones.

---

## Inicio rápido

1. Ejecuta `dist\main.exe`. No requiere instalar nada; solo un escritorio de Windows.
2. Pulsa **8** (Ejecutar simulación). Con la configuración por defecto la corrida dura 2 h simuladas, unos **2 minutos reales**.
3. Observa el monitor: temperatura, error y color del horno. Al terminar aparece **"CORRIDA TERMINADA"**.
4. Cierra el monitor. La consola muestra las **métricas de desempeño** y la ruta del archivo `.csv` con los resultados.

---

## Opciones del menú

| Opción | Qué hace |
|--------|----------|
| `1` Configurar PID | Ganancias Kp, Ki, Kd |
| `2` Configurar horno | T ambiente, setpoint, T máx. de equilibrio, **T inicial** (arranque en frío o en caliente), τ, Δt |
| `3` Fallos y perturbaciones | Activa o desactiva 6 perturbaciones: 3 sobre la **medición** y 3 sobre el **horno real** (ver abajo) |
| `4` Comparar corridas | **Dashboard**: elige corridas guardadas y las compara (tabla de métricas + curvas superpuestas) |
| `5` Anti-windup | Ninguno, recorte de la integral o **integración condicional** (por defecto) |
| `6` Velocidad y duración | x1, x10, **x60**, x600 o máxima · 30 min a 8 h (**2 h**) o sin límite |
| `7` Método numérico | **Euler**, Heun (RK2) o Runge-Kutta 4 · comparación con la solución exacta · estabilidad |
| `8` Ejecutar simulación | Abre el monitor y corre la simulación |
| `9` Salir | Cierra el simulador |

**Teclas:** `↑` `↓` para moverse, `Enter` para elegir, `1`–`9` para acceso directo y `Q` / `Esc` para salir. En los formularios, `Enter` sin escribir nada conserva el valor actual (entre paréntesis). Los decimales se escriben con **punto** (`0.5`).

---

## Experimentos sugeridos

| Experimento | Cómo | Qué se observa |
|---|---|---|
| **Windup** | Opción 5: *Ninguno* → ejecutar; luego *Integración condicional* → ejecutar | Sin anti-windup el horno se pasa ~280 °C; con él llega limpio a 1000 °C |
| **Límite del recorte** | Opción 1: Ki = 2; opción 5: *Recorte* → ejecutar; repetir con *Integración condicional* | Con recorte el horno no llega al setpoint; con integración condicional sí |
| **Orden de los métodos** | Opción 7 → *Comparar con la solución exacta* | Orden observado ≈ 1 (Euler), 2 (Heun) y 4 (RK4) |
| **Estabilidad numérica** | Opción 7 → *Estabilidad con Δt grande* | Con Δt > 2τ Euler diverge aunque la física sea estable |
| **Métodos en la simulación** | Opción 2: Δt = 30 s; opción 7: Euler y luego RK4 | Euler se aparta de RK4 con pasos grandes |
| **Arranque en caliente** | Opción 2: T inicial = 600 (o 1200) | Llega antes; desde 1200 °C el PID apaga la potencia y el horno se enfría |
| **Puerta abierta** | Opción 3: *Apertura de puerta* | Caídas de hasta ~50 °C en régimen y la recuperación del PID |
| **Red eléctrica** | Opción 3: *Fluctuación de la red* | La temperatura oscila ±3 °C alrededor del setpoint |
| **Sensor vs. realidad** | Opción 3: *Ruido del termopar* | El controlador lee ±1 °C de ruido, pero el horno apenas se mueve |

Para comparar dos corridas, cambia **una sola cosa** a la vez, usa la **misma duración** y luego abre la **opción 4 (Comparar corridas)**.

---

## Velocidad y duración (opción 6)

El horno real tarda más de una hora en llegar a 1000 °C. La **velocidad** comprime el tiempo de **ejecución**, no la física: con x60 cada segundo real equivale a un minuto simulado. El paso `Δt` y los resultados son los mismos a cualquier velocidad.

La **duración** son las horas **simuladas** tras las que la corrida se detiene sola, dejando las gráficas a la vista. Con la configuración por defecto el horno llega al setpoint hacia el minuto 74, así que **2 h** muestran la subida, la llegada y la estabilización.

---

## Método numérico (opción 7)

Elige con qué método se resuelve en cada paso la ecuación del horno, `dT/dt = (T_AMB − T)/τ + B·u`:

| Método | Orden | Evaluaciones de dT/dt por paso | Estable si |
|--------|-------|-------------------------------|------------|
| Euler | 1 | 1 | Δt < 2τ |
| Heun (RK2) | 2 | 2 | Δt < 2τ |
| Runge-Kutta 4 | 4 | 4 | Δt < ~2,785τ |

Un método de orden p reduce su error unas 2^p veces al dividir Δt a la mitad. Con el Δt por defecto (0,1 s) las curvas son casi idénticas.

- **Comparar con la solución exacta:** integra a potencia plena con Δt = 240, 120, 60, 30 y 15 s y compara con `T(t) = T_eq + (T0 − T_eq)·e^(−t/τ)`. Muestra una tabla de errores y órdenes observados, otra de costo frente a precisión, y una gráfica log-log cuya pendiente es el orden de cada método.
- **Estabilidad con Δt grande:** con la potencia apagada, cada método multiplica la desviación (T − T_AMB) por un factor R en cada paso. Con |R| > 1 diverge; por ejemplo, Euler con Δt = 2,5τ predice −7336 °C. **Solo Euler oscila**: Heun y RK4 tienen R > 0 y, cuando fallan, divergen sin oscilar.

---

## Métricas de desempeño

Al terminar cada corrida (o al detenerla, como "corrida incompleta") la consola muestra estas métricas, calculadas sobre la **temperatura real** del horno:

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

## Comparar corridas: dashboard (opción 4)

Muestra las **7 corridas guardadas más recientes**. Con `Enter` se marca o desmarca cada una (●/○); por defecto vienen marcadas las 2 últimas. Al elegir **Comparar seleccionadas**:

- la consola muestra una **tabla lado a lado** (A, B, C…) con la configuración de cada corrida (método, Δt, ganancias, anti-windup, T inicial, perturbaciones, duración) y sus métricas (sobrepaso, tiempos, error final, IAE e ISE). Avisa si las duraciones difieren, porque entonces IAE e ISE no son comparables;
- se abre una ventana con las **curvas superpuestas** de temperatura, error y potencia u, un color por corrida. En esta ventana sí se puede hacer zoom con la rueda.

---

## Resultados en archivo

Cada corrida se guarda automáticamente en la carpeta **`resultados`**:

- con `main.exe`: `simulador\dist\resultados\`
- desde el código: `simulador\resultados\`

El nombre indica la fecha, el método, el Δt y el anti-windup, por ejemplo `2026-10-08_143015_rk4_dt0,1_condicional.csv`, y la consola muestra la ruta al salir. El archivo se abre directamente en **Excel en español** (separador `;`, coma decimal):

- las primeras filas (`#`) guardan la configuración y las métricas;
- luego hay una fila por segundo simulado con `t_s`, `T_C` (temperatura real), `T_set_C`, `error_C` (el error que vio el controlador, incluidas las perturbaciones) y `u` (potencia, de 0 a 1).

---

## Modelo y control

- **Modelo térmico:** sistema de **primer orden**, con pérdidas al ambiente según la **Ley de Enfriamiento de Newton** más la potencia del calentador:
  `dT/dt = (T_AMB − T)/τ + B·u`, con `u ∈ [0, 1]` (un horno no enfría activamente).
  La ganancia `B = (T_MAX_EQ − T_AMB)/τ` se deriva de la temperatura de equilibrio a potencia plena (1300 °C por defecto), lo que da un calentamiento máximo realista de ~0,42 °C/s.
- **PID** (por defecto Kp = 200, Ki = 10, Kd = 2):
  - **Proporcional:** responde al error instantáneo.
  - **Integral:** corrige el error acumulado (regla del trapecio), protegida por el **anti-windup**.
  - **Derivativa:** se calcula sobre la **temperatura medida**, para evitar picos cuando el error salta.
- **Fallos y perturbaciones (opción 3)**, todas apagadas por defecto:

  | Sobre la **medición** (el controlador lee mal) | Sobre el **horno real** (cambia la física) |
  |---|---|
  | Error oscilante: senoide de 20 °C + ruido | Apertura de puerta: ~2 por hora, 90 s, las pérdidas se triplican |
  | Impulsos en el error: ±80 °C, ~6 por hora | Fluctuación de la red: voltaje ±6 % → potencia ±12 % (P ∝ V²) |
  | Ruido del termopar: ±1 °C gaussiano | Ambiente variable: ±10 °C en 1 h (el PID lo compensa casi por completo) |

  Con las del horno, la temperatura sigue moviéndose alrededor del setpoint como en un horno real. Las tres actúan dentro de la misma ecuación `dT/dt`, sea cual sea el método numérico.

---

## Instalación y desarrollo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt                          # ejecutar
pip install -r requirements.txt -r requirements-dev.txt  # + PyInstaller y pytest
python main.py                                           # desde la carpeta simulador/
python -m pytest                                         # pruebas automáticas (también corren en GitHub Actions en cada push)
pyinstaller main.spec --noconfirm --clean                # regenerar dist\main.exe
```

Dependencias principales: `rich` (consola), `readchar` (teclado), `pyqtgraph` + `PySide6` (monitor gráfico) y `numpy`. Requiere un escritorio con interfaz gráfica (Qt). Para regenerar `main.exe`, el simulador debe estar **cerrado**.

## Estructura del proyecto

```text
simulador/
├── main.py  main.spec          # punto de entrada · configuración de PyInstaller
├── requirements*.txt           # dependencias (ejecución / desarrollo)
├── CLAUDE.md  README.md        # guía técnica · esta guía
├── pytest.ini  tests/          # pruebas automáticas
├── documentos/                 # planes de trabajo futuros
├── dist/  build/  resultados/  # ejecutable · compilación · CSV (no se versionan)
└── simulador_horno/
    ├── app.py                  # bienvenida + bucle del menú
    ├── configuracion/          # ¿con qué parámetros?   horno, PID, simulación, límites
    ├── modelo/                 # ¿qué se simula?        horno, perturbaciones, actuador
    ├── control/                # ¿quién controla?       PID, anti-windup, saturación, error
    ├── numerico/               # ¿con qué método?       integradores, comparación, estabilidad
    ├── simulacion/             # ¿quién coordina?       motor, reloj, historial, métricas, resultados, simulador
    ├── interfaz/               # ¿qué ve el usuario?    consola (rich), gráficas (pyqtgraph), alarmas
    └── estilos/                # ¿cómo se ve?           tema visual
```

---

## Contacto

**Omar Alberto Torres**  
**Tel:** [+57 304 344 0112](tel:+573043440112)  
**Correo:** [omara.torres@udea.edu.co](mailto:omara.torres@udea.edu.co)

> Si necesitan información adicional sobre la ejecución o detalles técnicos del proyecto, escríbanme al correo institucional. También pueden revisar los comentarios del código fuente para aclaraciones rápidas.
