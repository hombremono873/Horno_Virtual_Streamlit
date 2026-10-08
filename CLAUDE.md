# CLAUDE.md

Guía para entender y modificar este código. Léela antes de tocar nada.

## Qué es

Simulador de consola del **calentamiento de un horno eléctrico regulado por un controlador PID**. Es un trabajo académico y **pedagógico** de *Métodos Numéricos* (Universidad de Antioquia; autor Omar Alberto Torres, docente Yony Ceballos). La planta es un horno: no hay motor ni otro actuador mecánico.

El usuario configura el PID, el horno y la velocidad desde un menú de consola (`rich` + `readchar`) y lanza la simulación. La corrida muestra a la vez una tabla viva en la consola y una ventana Qt (`pyqtgraph` + `PySide6`) con las curvas de temperatura y error y la "colorimetría" térmica del horno.

La física es realista: el horno tarda ~1 h simulada en llegar a 1000 °C. Para que un estudiante no espere tanto, **se comprime el tiempo de ejecución, no el modelo**. Hay un factor de velocidad (x1, x10, x60, x600 o máxima) y `DT` nunca cambia por eso.

Todos los identificadores, comentarios y textos de interfaz están en **español**. Mantén esa convención.

## Comandos

Todo se ejecuta **desde la carpeta `simulador/`**: `main.py` importa el paquete `simulador_horno` de forma relativa al CWD.

```bash
# Entorno (Windows, Python 3.13)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt                          # solo ejecución
pip install -r requirements.txt -r requirements-dev.txt  # + PyInstaller y pytest

# Ejecutar
python main.py

# Pruebas (no necesitan pantalla; ~1 s)
python -m pytest            # -s para ver las métricas de la corrida por defecto

# Regenerar el ejecutable dist/main.exe (onefile, ~64 MB). NO se regenera solo.
pyinstaller main.spec --noconfirm --clean
```

- **Requiere escritorio (Qt).** Sin pantalla, usa `QT_QPA_PLATFORM=offscreen` para probar el bucle visual.
- El menú necesita una terminal real: `readchar` lee teclas sin Enter.
- Si `.venv` falla al activarse (rutas viejas incrustadas tras copiar la carpeta), recréalo con `python -m venv .venv --clear` y reinstala.

## Arquitectura

Cada carpeta de `simulador_horno/` responde a una pregunta:

```
simulador_horno/
├── app.py            # arranque: bienvenida + bucle del menú
├── configuracion/    # ¿con qué parámetros?   parametros_horno, parametros_pid, parametros_simulacion,
│                     #                        parametros_electricos, limites
├── modelo/           # ¿qué se simula?        horno (ecuación + Euler), perturbaciones, actuador
├── control/          # ¿quién controla?       pid, anti_windup, escalado, senal_error
├── numerico/         # ¿con qué método?       integradores (Euler, Heun, RK4 elegibles; tabla METODOS),
│                     #                        comparacion (vs. solución exacta, orden de convergencia),
│                     #                        estabilidad (factor de amplificación, límites de Δt)
├── simulacion/       # ¿quién coordina?       motor (lógica), reloj (velocidad), historial, simulador (visual)
├── interfaz/         # ¿qué ve el usuario?    consola/, graficas/, alarmas/
└── estilos/          # ¿cómo se ve?           tema (paleta y medidas)
```

Flujo de ejecución:

```
main.py  ->  simulador_horno/app.py::ejecutar()
                 │
                 ├── interfaz/consola   (menú, formularios)  ──escribe──►  configuracion/*
                 │
                 └── simulacion/Simulador.ejecutar()            (REFRESCO_HZ = 4 veces por segundo real)
                        │  en cada refresco:
                        ├─► simulacion/reloj.pasos_por_refresco(factor, DT, HZ)  -> N pasos
                        ├─► simulacion/Motor.avanzar(N)   y en cada uno de los N pasos:
                        │      ├─► control/senal_error.construir_error(t, T)
                        │      ├─► control/pid.actualizar_pid(error)       -> u ∈ [0, 1]
                        │      ├─► numerico/integradores.METODOS[metodo](T, u)  (Euler, Heun o RK4)
                        │      └─► simulacion/historial.registrar(...)     (1 muestra / s simulado)
                        ├─► interfaz/consola/tabla_vivo.generar_tabla(...)  (rich.Live)
                        ├─► interfaz/graficas/panel.PanelGraficas.actualizar(...)
                        └─► dormir el resto de 1/REFRESCO_HZ (en "máxima" no duerme)
```

| Capa | Ruta | Responsabilidad | Regla |
|---|---|---|---|
| Configuración | `configuracion/` | Parámetros y estado global | Sin lógica (salvo `recalcular_B`) |
| Modelo | `modelo/` | Ecuación del horno, perturbaciones, actuador | **Sin E/S** |
| Control | `control/` | PID, anti-windup, saturación, señal de error | **Sin E/S** (excepción: ver la deuda técnica, punto 4) |
| Numérico | `numerico/` | Métodos de integración alternativos | **Sin E/S** |
| Simulación | `simulacion/` | `Motor` y `reloj` sin E/S; `Simulador` orquesta la pantalla | `motor` y `reloj` **no importan rich ni Qt** (hay prueba) |
| Interfaz | `interfaz/` | Consola rich, ventana Qt, beep | Sin cálculo de control |
| Estilos | `estilos/` | Paleta y medidas visuales | Solo constantes |

### Estado global: módulos de `configuracion/` como variables mutables

Este punto es el más importante para entender el código. **No hay objetos de configuración.** El estado vive en variables de módulo que se importan con alias y se mutan en caliente:

- `configuracion/parametros_horno.py` (alias habitual `var`, `vhorno`, `horno`):
  - `T_AMB=30`, `T_SET=1000`, `T_MAX_EQ=1300` (equilibrio con u = 1), `T_INICIAL=30`, `TAU=3000` y `DT=0.1`.
  - **`T_INICIAL`** es la temperatura con que arranca cada corrida (`Motor.T`). Igual a `T_AMB` es arranque en frío y mayor es en caliente. El formulario exige `T_AMB ≤ T_INICIAL ≤ T_MAX_EQ`. Si se arranca en el setpoint, el PID empieza con la integral en cero, decide u = 0 y el horno se enfría un poco antes de recuperarse: es el "bache" real de reencender un controlador sin memoria.
  - **`B` es derivado:** `recalcular_B()` hace `B = (T_MAX_EQ − T_AMB)/TAU` ≈ 0,423 °C/s. Llámala siempre que cambies `T_AMB`, `TAU` o `T_MAX_EQ` (lo hacen el formulario y el `Motor`).
  - También guarda las listas del historial (`tiempos`, `temperaturas`, `errores`, `potencias`) y los flags de perturbación (`error_oscilante`, `flag_error`, `delta_T`).
- `configuracion/parametros_pid.py` (alias `var`, `vpid`, `pid`): `KP=200`, `KI=10`, `KD=2`, `anti_windup="condicional"`, `restringir_integral=0.85` (factor del modo "recorte") y el estado interno del PID entre pasos (`error_prev`, `integral`, `derivada`, `proporcional`). `Motor` pone ese estado a cero al iniciar cada corrida.
- `configuracion/parametros_simulacion.py` (alias `vsim`, `sim`): `velocidad="x60"` (clave de `limites.VELOCIDADES`), `duracion_horas=2` (de `limites.DURACIONES_HORAS`; `None` = sin límite) y `metodo="euler"` (clave de `numerico.integradores.METODOS`).
- `configuracion/parametros_electricos.py`: `angulo_conduccion` (no se usa en el bucle).
- `configuracion/limites.py`: constantes **fijas** que el menú no edita:
  - control: `U_MAX=20000`, `UMBRAL_INTEGRAL=2000` (tope del modo "recorte");
  - velocidad y duración: `VELOCIDADES` (`None` = máxima), `DURACIONES_HORAS = (0.5, 1, 2, 4, 8, None)` y `REFRESCO_HZ=4`;
  - historial: `INTERVALO_MUESTREO=1.0` s simulado y `MAX_MUESTRAS` (`HORAS_HISTORIAL=12` h);
  - archivos: `CARPETA_RESULTADOS="resultados"`, `CSV_SEPARADOR=";"` y `CSV_DECIMAL=","` (Excel en español);
  - impulso: `TASA_IMPULSOS_HORA=6`, `DURACION_IMPULSO=3` s, `MAGNITUD_IMPULSO=80` °C;
  - colores y actuador: rango de color 30–1200 °C y `THETA_MIN/MAX`.
- `estilos/tema.py`: paleta y medidas compartidas por la consola (estilos rich `C_*`) y las gráficas (colores hex `G_*`, colormap `plasma`, tamaño de ventana).

Siempre importa el **módulo** (`from simulador_horno.configuracion import parametros_horno as vhorno`) y lee `vhorno.T_SET` en el momento de usarlo. Nunca hagas `from ...parametros_horno import T_SET`: copiarías el valor y no verías los cambios del menú.

## Modelo numérico

**Planta** ([modelo/horno.py](simulador_horno/modelo/horno.py)): sistema de primer orden

```
dT/dt = (1/TAU)·(T_AMB − T) + B·u          u ∈ [0, 1],  B = (T_MAX_EQ − T_AMB)/TAU
T[k+1] = T[k] + DT·dT/dt                    (Euler explícito)
```

Con u = 1 la temperatura tiende a `T_MAX_EQ`. Protege contra `TAU == 0` y contra resultados NaN o infinitos (devuelve `T_actual`). [integradores.py](simulador_horno/numerico/integradores.py) contiene la misma ecuación con Heun (RK2) y RK4 (`simular_horno_heun` y `simular_horno_runge`). La tabla `METODOS` asocia `"euler"`, `"heun"` y `"rk4"` con su función de paso, todas con firma `(T, u) -> T_nuevo`, y `NOMBRES` guarda el nombre visible. El usuario elige el método en la opción 7 del menú. `Motor` lo fija al crearse (`self.metodo`, `self._integrar`), así que no cambia a mitad de una corrida. `tests/test_integradores.py` comprueba contra la solución exacta que el orden de convergencia observado es 1, 2 y 4. `ORDEN` y `EVALUACIONES` guardan la teoría de cada método.

**Comparación con la solución exacta** ([numerico/comparacion.py](simulador_horno/numerico/comparacion.py), sin E/S): `comparar()` integra a potencia plena (u = 1) desde `T_AMB` durante `HORIZONTE = 3600` s con cada método y cada Δt de `DTS_COMPARACION = (240, 120, 60, 30, 15)`. Devuelve un `ResultadoComparacion` con las `Trayectoria` (tiempos, temperaturas, errores, `error_maximo`, `evaluaciones`) y los órdenes observados `log(e1/e2)/log(dt1/dt2)`. Como los integradores leen `parametros_horno.DT`, `integrar()` lo cambia temporalmente y **siempre lo restaura** en un `finally`. La interfaz lo presenta con `interfaz/consola/comparacion.py` (tablas rich) e `interfaz/graficas/comparacion.py` (`VentanaComparacion`). Se accede desde el submenú de la opción 7, en la entrada "Comparar con la solución exacta".

**Estabilidad con Δt grande** ([numerico/estabilidad.py](simulador_horno/numerico/estabilidad.py), sin E/S): el horno se enfría desde `T_SET` con u = 0, que es la ecuación de prueba `y' = λy` con λ = −1/TAU. `factor_amplificacion(metodo, dt)` da R(z) con z = −Δt/TAU: Euler `1+z`, Heun `1+z+z²/2` y RK4, la serie de e^z hasta z⁴. `limite_estabilidad` busca por bisección el Δt con |R| = 1: 2τ para Euler y Heun, ~2,785τ para RK4. `estudiar()` integra con Δt = `FRACCIONES_TAU` (0,5; 1,5; 2,5; 3)·τ, elegidos para mostrar los cuatro casos: todos estables, Euler oscila, Euler y Heun divergen con RK4 estable, y todos divergen. Reutiliza `comparacion.integrar` con `T0` y `u=0`. Interfaz: `interfaz/consola/estabilidad.py` y `interfaz/graficas/estabilidad.py` (`VentanaEstabilidad`, rejilla 2×2 con el eje Y acotado para que las divergencias salgan del cuadro). Se accede desde la entrada "Estabilidad con Δt grande" del submenú de la opción 7.

**Error** ([control/senal_error.py](simulador_horno/control/senal_error.py)): `error = T_SET − T`, más perturbaciones opcionales:
- `error_oscilante` (opción 3 del menú): `get_ruido(t) = 20·sin(0.05·t) + U(−0.5, 1.5)`.
- `flag_error` (opción 4): `perturbacion_total(t, dt, tasa_hora, duracion, magnitud)`, que suma ruido, senoide y un impulso ([modelo/perturbaciones.py](simulador_horno/modelo/perturbaciones.py)).
  - La tasa se expresa **por hora simulada** y se convierte a probabilidad por paso con `p = 1 − exp(−tasa·DT/3600)`, así que la frecuencia no depende de `DT`.
  - El signo es **constante durante cada impulso** y alterna de un impulso al siguiente (el primero es negativo).
  - Cada impulso suena **una vez, al empezar**. El beep (`interfaz/alarmas/sonora.py`, `winsound`, solo Windows) corre en un hilo para no bloquear la simulación.
- Las perturbaciones se suman **al error del PID, no a la planta**.

**PID** ([control/pid.py](simulador_horno/control/pid.py)):
- `calcular_pid(error, error_prev, integral, medida, medida_prev)` es **pura**. Integra con la regla del trapecio y deriva **sobre la medición**, `−(medida − medida_prev)/DT`, en lugar de sobre el error. Con el setpoint fijo da la misma acción D, pero evita el pico (*derivative kick*) cuando el error salta, como en el primer paso, donde antes D valía `KD·970/DT = 19 400`. Si `medida_prev` es `None`, D = 0. Devuelve `(u_escalado, integral, error, KD·derivada, KP·error)`.
- `actualizar_pid(error, medida)` llama a la anterior y persiste el estado en `parametros_pid`, incluida `medida_prev`. `Motor` pasa `medida = T_SET − error`, lo que "lee" el controlador, perturbaciones incluidas, y pone `medida_prev = None` al iniciar cada corrida.
- Anti-windup ([anti_windup.py](simulador_horno/control/anti_windup.py)), elegible en la opción 5 del menú (`parametros_pid.anti_windup`). `calcular_pid` calcula la integral nueva por trapecio y la salida sin saturar `u_bruta`, y `limitar(modo, integral_previa, integral_nueva, error, u_bruta)` decide qué integral se conserva:
  - `"ninguno"`: integra siempre. Con las ganancias por defecto la integral llega a ~1,6 millones y el sobrepaso es de ~29 %; sirve para mostrar el windup.
  - `"recorte"`: el método original, que reproduce bit a bit el comportamiento anterior. Si la integral supera `UMBRAL_INTEGRAL` se multiplica por `restringir_integral`. **Con KI bajo deja error permanente** (KI = 5: 28 °C; KP = 50 y KI = 2: 176 °C).
  - `"condicional"` (**por defecto**): integración condicional o *clamping*. No integra si `u_bruta > 1` y el error es positivo, ni si `u_bruta < 0` y el error es negativo. Llega al setpoint con cualquier sintonía.
- Saturación ([escalado.py](simulador_horno/control/escalado.py)): `u = clamp(u_bruto / U_MAX, 0, 1)`. Un horno no enfría activamente.
- **Desempeño por defecto** (lo verifica `tests/test_control.py`): 90 % a los 58 min, sobrepaso del 0,54 % (0,27 % con el modo "recorte"), banda de ±1 % a los 71 min y error final de 0 °C. La subida está limitada por la física (u = 1 toda la rampa), no por las ganancias.

**Actuador** ([modelo/actuador.py](simulador_horno/modelo/actuador.py)): convierte `u` en un ángulo de disparo `θ ∈ [THETA_MIN, THETA_MAX]` con un suavizado aleatorio. **No se usa** en el bucle.

## Bucle de simulación y velocidad

- [simulacion/motor.py](simulador_horno/simulacion/motor.py), clase `Motor`: la lógica pura de la corrida.
  - `__init__` reinicia el estado del PID y del impulso, recalcula B y limpia el historial.
  - `paso()` calcula el error y aplica el PID, **registra** la muestra `(t, T, error, u)` y luego avanza la planta y suma `DT` a `t`. Registrar antes de integrar hace que cada muestra sea coherente en el instante t.
  - `avanzar(n)` ejecuta n pasos. Guarda `T`, `t`, `u` y `error`.
- [simulacion/reloj.py](simulador_horno/simulacion/reloj.py): `pasos_por_refresco(factor, dt, hz, acumulado)` devuelve `N = factor/(hz·dt)`. Acumula la fracción sobrante para que x1 (2,5 pasos por refresco) también sea exacto.
- [simulacion/simulador.py](simulador_horno/simulacion/simulador.py), clase `Simulador`: el bucle visual.
  - En cada refresco (4 por segundo real) avanza N pasos del motor, actualiza la tabla y el panel y duerme el resto del periodo.
  - En modo **máxima** ejecuta lotes de `LOTE_MAXIMA` pasos durante todo el periodo y no duerme.
  - **Duración:** `Simulador.duracion` (s simulados, fija por corrida) sale de `vsim.duracion_horas`. `reloj.pasos_restantes(t, duracion, dt)` limita los pasos de cada refresco, también en "máxima", así que la corrida se detiene **exactamente** en la duración. Con `terminada` en True el bucle **sigue refrescando sin avanzar**: el monitor responde, la tabla muestra "CORRIDA TERMINADA" y el eje X del panel abarca `[0, duración]` desde el inicio.
  - Se vuelve al menú al **cerrar la ventana Qt** (`panel.abierta == False`) o con **Ctrl+C**.
  - **Métricas** ([simulacion/metricas.py](simulador_horno/simulacion/metricas.py), sin E/S): `calcular(tiempos, temperaturas, T_set)` devuelve un `Metricas` calculado sobre la temperatura REAL, no sobre el error, que puede llevar perturbaciones. Incluye sobrepaso en el sentido del salto, de modo que si se arranca por encima del setpoint se mide por debajo; t10, t90, tiempo de subida, establecimiento en ±1 %, error final, e IAE/ISE por trapecio. Los tiempos no alcanzados valen `None`. `Simulador` las calcula una vez, al terminar (`_tabla`) o al detenerse (`_finalizar`). La tabla en vivo las muestra en lugar de las barras de nivel, y `_finalizar` las imprime y **siempre espera una tecla** para que el menú no las borre. Presentación en `interfaz/consola/metricas.py`, con IAE en °C·min.
- [historial.py](simulador_horno/simulacion/historial.py): `Historial` envuelve las listas de `parametros_horno` (comparte referencia). Guarda **una muestra cada `INTERVALO_MUESTREO` s simulados** y recorta a `MAX_MUESTRAS`, así que el arranque completo se ve a cualquier velocidad. Registra también la potencia `u` (`potencias`).
- [resultados.py](simulador_horno/simulacion/resultados.py): `guardar(historial, T_set, parametros, metricas)` escribe **un CSV por corrida** en `carpeta_resultados()`, que está junto al exe si está empaquetado (`sys.frozen`) o en el CWD. Usa UTF-8 con BOM, `;` y coma decimal; primero las líneas `# clave;valor` con la configuración y las métricas (`metrica_*`), después las columnas `t_s;T_C;T_set_C;error_C;u`. `leer(ruta)` devuelve `(parametros, series)` y será la base del dashboard. `Simulador._finalizar` guarda al salir y muestra la ruta; un `OSError` solo se avisa. La carpeta `resultados/` está en `.gitignore`.
- El motor da ~1,3 millones de pasos por segundo real (~0,8 µs por paso). Por eso x600 es holgado y "máxima" simula decenas de horas en pocos segundos.

## Interfaz

- [app.py](simulador_horno/app.py) muestra la bienvenida y luego el bucle de menú, que despacha con el dict `ACCIONES` (`"1"`–`"8"`). `OPCION_SIMULAR = "8"` vuelve sin pausa y `OPCION_SALIR = "9"`.
- [interfaz/consola/marco.py](simulador_horno/interfaz/consola/marco.py) es el marco común de todas las pantallas (encabezado, migas, pie de atajos) y el único `Console` compartido (`marco.console`). Contiene además:
  - lectura de teclas: `leer_tecla`, que convierte Ctrl+C en `KeyboardInterrupt`;
  - el menú navegable `menu_interactivo(…, inicial=)` (flechas y Enter, teclas 1-9; Q o Esc devuelven la última opción);
  - las ayudas de formulario `pedir_float` (Enter conserva el valor actual), `confirmar` y `resumen`;
  - `panel_estado`, el resumen de la configuración que acompaña al menú, incluida la velocidad.
- [menu.py](simulador_horno/interfaz/consola/menu.py) define `ITEMS`, la lista de opciones `(clave, etiqueta, descripción)`.
- [formularios.py](simulador_horno/interfaz/consola/formularios.py) escribe directamente en los módulos de `configuracion/`. Contiene:
  - los conmutadores de perturbación (`_conmutar`);
  - `configurar_horno`, que pide `T_MAX_EQ` (no B), valida que `T_MAX_EQ > T_AMB`, `TAU > 0` y `DT > 0`, y llama a `recalcular_B`;
  - `configurar_velocidad` y `configurar_metodo`, submenús con `menu_interactivo` cuyo último ítem es "Volver". El de método incluye "Comparar con la solución exacta" (`comparar_metodos()`) y "Estabilidad con Δt grande" (`estudiar_estabilidad()`).
- [tabla_vivo.py](simulador_horno/interfaz/consola/tabla_vivo.py): `generar_tabla(t, T, T_set, u, error, pid, horno, acciones, velocidad, t_real)` construye el panel de rich. Muestra el reloj (tiempo simulado en hh:mm:ss, velocidad y tiempo real), las lecturas, las barras (u en [0, 1]), los términos P/I/D y la configuración.
- [interfaz/graficas/panel.py](simulador_horno/interfaz/graficas/panel.py): `PanelGraficas` es una única ventana `GraphicsLayoutWidget`.
  - Tiene cuatro vistas: temperatura frente al tiempo con la línea del setpoint, error frente al tiempo, el corte del horno coloreado por T (colorimetría) y la franja histórica de color, más una barra de escala en °C.
  - **El eje de tiempo está en minutos simulados.** La franja lee del historial, igual que las curvas.
  - Las gráficas de tendencia y error **no responden al ratón** (sin zoom, arrastre ni menú). En pyqtgraph un giro de rueda desactiva el ajuste automático y la vista se congela mientras la corrida sigue.
  - **El eje Y está centrado en el setpoint** (y el del error en 0) con la misma escala, para que se vea cuánto se aleja la temperatura por arriba o por debajo. El semirango sale de la máxima desviación de los últimos `G_VENTANA_ESCALA_MIN = 30` min simulados (`_semirango`), con `G_HOLGURA_ESCALA` y un mínimo de `G_SEMIRANGO_MIN = ±5 °C` (en `estilos/tema.py`). La escala es amplia durante la subida y se cierra al estabilizarse: así se ve la oscilación amortiguada de ~2,6 °C que en una escala de 0 a 1000 °C sería invisible. Los ejes no usan prefijos SI (`enableAutoSIPrefix(False)`).
  - Las curvas se diezman al dibujar (`setDownsampling(method="peak")`): con 12 h de historial, unas 43 200 muestras, cada refresco tarda ~25 ms.
  - Su API es `actualizar(tiempos, temps, errs, T, T_set)` (tiempos en segundos), `abierta` y `cerrar()`.
  - El modelo es **síncrono**: cada `actualizar` llama a `app.processEvents()`, sin hilos ni `QTimer`.
- [interfaz/graficas/comparacion.py](simulador_horno/interfaz/graficas/comparacion.py): `VentanaComparacion(resultado)` es una ventana **estática** con tres vistas: las curvas frente a la exacta con el Δt mayor, el error absoluto en el tiempo en escala log y la convergencia log-log, cuya pendiente es el orden. `mostrar_y_esperar()` usa `app.exec()` y bloquea hasta que se cierra. Es compatible con el monitor síncrono en la misma sesión (verificado).

## Pruebas

`tests/` usa pytest (configurado en `pytest.ini`, con `pythonpath = .`). Las pruebas no importan rich ni Qt. El fixture `configuracion_limpia` de [conftest.py](tests/conftest.py) guarda y restaura los módulos de configuración en cada prueba: las listas se restauran en sitio porque `Historial` comparte la referencia.

| Archivo | Comprueba |
|---|---|
| `test_fisica.py` | u = 1 converge a `T_MAX_EQ`; B se recalcula al cambiar T_AMB, TAU o T_MAX_EQ |
| `test_control.py` | u ∈ [0, 1] en 4 h (con y sin perturbaciones); métricas de la corrida por defecto (sobrepaso < 5 %) |
| `test_velocidad.py` | simulado/real = factor para cada velocidad y varios DT, sin `time.sleep` |
| `test_duracion.py` | con el bucle real de `Simulador._avanzar_refresco`: cada velocidad se detiene exactamente en la duración y ya no avanza; x600 tarda los refrescos esperados; sin límite nunca termina |
| `test_panel.py` | (Qt offscreen) la franja termina en el mismo minuto que las curvas; con duración el eje X abarca la corrida completa y el error queda alineado |
| `test_historial.py` | conserva ≥ 4 h; una muestra por segundo simulado sea cual sea DT |
| `test_perturbaciones.py` | la tasa de impulsos no cambia con DT (semilla fija); el signo es constante en el impulso y alterna entre impulsos |
| `test_integradores.py` | cada método converge a `T_MAX_EQ`; Euler > Heun > RK4 en error; orden observado 1, 2 y 4 frente a la solución exacta; el motor usa el método elegido |
| `test_comparacion.py` | orden observado ≈ teórico para cada Δt; más orden, menos error; el costo en evaluaciones; Δt del usuario restaurado incluso si falla |
| `test_estabilidad.py` | factores R teóricos; límites 2τ, 2τ y 2,785τ; el código real amplifica exactamente por R; el comportamiento observado coincide con el veredicto |
| `test_anti_windup.py` | sin anti-windup hay windup (sobrepaso > 20 %); el condicional llega al setpoint con cualquier sintonía; el recorte deja error con KI bajo; la regla de integración condicional |
| `test_derivada.py` | sin pico de D en el primer paso; con el setpoint fijo equivale a derivar el error, también con perturbaciones; `medida_prev` se reinicia en cada corrida |
| `test_metricas.py` | respuesta de primer orden: t10, t90, establecimiento, IAE e ISE coinciden con las fórmulas; sobrepaso; arranque por encima del setpoint; las métricas distinguen los anti-windup |
| `test_resultados.py` | ida y vuelta del CSV; formato para Excel (BOM, `;`, coma decimal); el historial registra u; el simulador guarda y no se rompe si la carpeta falla |
| `test_arranque.py` | arranque en frío por defecto; cada corrida empieza en `T_INICIAL` y llega al setpoint; en caliente llega antes; por encima del setpoint apaga la potencia y se enfría |
| `test_capas.py` | `motor`, `reloj`, `metricas` y `resultados` no importan rich, PySide6 ni pyqtgraph |

## Cómo añadir cosas

- **Nueva opción de menú:** añade una tupla en `menu.ITEMS`, la función en `formularios.py` y la entrada en `app.ACCIONES`. Si cambia el número de opciones, revisa `ATAJOS_MENU` en `marco.py`, `OPCION_SIMULAR` y `OPCION_SALIR` en `app.py` y la tabla de controles del README.
- **Nuevo parámetro editable:** añádelo como variable de módulo en `configuracion/parametros_*.py`, pídelo en el formulario correspondiente, muéstralo en `marco.panel_estado` y en `tabla_vivo`, y añade su módulo a `_MODULOS` en `tests/conftest.py` si es un archivo nuevo.
- **Constante interna:** `configuracion/limites.py`. **Colores y estilos:** `estilos/tema.py`.
- **Nueva velocidad:** basta con añadirla a `limites.VELOCIDADES` y a `_DESCRIPCION_VELOCIDAD` en `formularios.py`.
- **Nuevo método numérico:** escribe la función de paso `(T, u) -> T_nuevo` en `numerico/integradores.py` y añádela a `METODOS`, a `NOMBRES`, a `_DESCRIPCION_METODO` en `formularios.py` y a `ORDEN` en `tests/test_integradores.py`.
- **Para acelerar, nunca agrandes `DT`:** cambia la velocidad. `DT` es un parámetro numérico.
- **Nueva dependencia:** fija la versión en `requirements.txt`. Si PyInstaller no la detecta, añádela a `hiddenimports` o `datas` en `main.spec`. Por ejemplo, `readchar` necesita `copy_metadata` y `pyqtgraph` necesita `collect_data_files`.
- Ejecuta `python -m pytest` antes de cada commit.

## Deuda técnica y trampas conocidas

1. Las perturbaciones afectan al **error**, no a la física. `delta_T` se calcula pero `simular_horno` no lo usa.
2. **El modo "recorte" (el anti-windup original) limita la sintonía.** Se conserva para comparar, pero ya no es el predeterminado. No acota la integral negativa, y la positiva queda topada en ~`UMBRAL_INTEGRAL`. En el equilibrio el horno necesita u ≈ 0,76, es decir `KI·integral/U_MAX ≈ 0,76`, así que con KI bajo queda **error permanente**. El modo "condicional", el predeterminado, no tiene este problema.
3. El estado del impulso vive en atributos de la función `impulso_probabilistico` (se reinicia con `reiniciar_impulso()`). Debería ser un objeto.
4. `senal_error.py` (capa de control) importa `interfaz.alarmas.sonora`. Es una violación de capas pendiente: debería notificar la simulación.
5. La integral del primer paso usa `error_prev = 0` en el trapecio: suma media área del primer error. El efecto es despreciable. El *derivative kick* ya está resuelto con la derivada sobre la medición.
6. `modelo/actuador.py` (ángulo de conducción) existe pero no está conectado, así que PyInstaller no lo incluye en el exe.
7. El README menciona la Ley de Fourier, pero el modelo solo tiene pérdidas tipo Newton más la entrada de control.
8. **Modo "máxima" con duración "sin límite":** simula ~70 h en 3 s reales y, con un historial de 12 h, el arranque se pierde enseguida. Con cualquier duración finita, el comportamiento por defecto, ya no ocurre.

## Archivos fuera del paquete

- `main.spec`: configuración de PyInstaller (onefile, consola). Excluye matplotlib, tkinter y PyQt5/6.
- `requirements.txt`: dependencias de ejecución. `requirements-dev.txt`: PyInstaller, pytest y sus dependencias.
- `pytest.ini` y `tests/`: pruebas automáticas.
- `build/` y `dist/`: artefactos generados, ignorados por git.
- `README.md`: documentación para el usuario final, con datos de contacto del autor.
