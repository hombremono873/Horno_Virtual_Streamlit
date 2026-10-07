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
├── numerico/         # ¿con qué método?       integradores (Heun, RK4)
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
                        │      ├─► modelo/horno.simular_horno(T, u)        (Euler)
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
  - `T_AMB=30`, `T_SET=1000`, `T_MAX_EQ=1300` (equilibrio con u = 1), `TAU=3000` y `DT=0.1`.
  - **`B` es derivado:** `recalcular_B()` hace `B = (T_MAX_EQ − T_AMB)/TAU` ≈ 0,423 °C/s. Llámala siempre que cambies `T_AMB`, `TAU` o `T_MAX_EQ` (lo hacen el formulario y el `Motor`).
  - También guarda las listas del historial (`tiempos`, `temperaturas`, `errores`) y los flags de perturbación (`error_oscilante`, `flag_error`, `delta_T`).
- `configuracion/parametros_pid.py` (alias `var`, `vpid`, `pid`): `KP=200`, `KI=10`, `KD=2`, `restringir_integral=0.85` y el estado interno del PID entre pasos (`error_prev`, `integral`, `derivada`, `proporcional`). `Motor` pone ese estado a cero al iniciar cada corrida.
- `configuracion/parametros_simulacion.py` (alias `vsim`, `sim`): `velocidad="x60"`, una clave de `limites.VELOCIDADES`.
- `configuracion/parametros_electricos.py`: `angulo_conduccion` (no se usa en el bucle).
- `configuracion/limites.py`: constantes **fijas** que el menú no edita:
  - control: `U_MAX=20000`, `UMBRAL_INTEGRAL=2000`;
  - velocidad: `VELOCIDADES` (`None` = máxima), `REFRESCO_HZ=4`;
  - historial: `INTERVALO_MUESTREO=1.0` s simulado y `MAX_MUESTRAS` (5 h);
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

Con u = 1 la temperatura tiende a `T_MAX_EQ`. Protege contra `TAU == 0` y contra resultados NaN o infinitos (devuelve `T_actual`). [integradores.py](simulador_horno/numerico/integradores.py) contiene la misma ecuación con Heun (RK2) y RK4 (`simular_horno_heun` y `simular_horno_runge`), pero **no están conectados** al bucle ni al menú.

**Error** ([control/senal_error.py](simulador_horno/control/senal_error.py)): `error = T_SET − T`, más perturbaciones opcionales:
- `error_oscilante` (opción 3 del menú): `get_ruido(t) = 20·sin(0.05·t) + U(−0.5, 1.5)`.
- `flag_error` (opción 4): `perturbacion_total(t, dt, tasa_hora, duracion, magnitud)`, que suma ruido, senoide y un impulso ([modelo/perturbaciones.py](simulador_horno/modelo/perturbaciones.py)).
  - La tasa se expresa **por hora simulada** y se convierte a probabilidad por paso con `p = 1 − exp(−tasa·DT/3600)`, así que la frecuencia no depende de `DT`.
  - El signo es **constante durante cada impulso** y alterna de un impulso al siguiente (el primero es negativo).
  - Cada impulso suena **una vez, al empezar**. El beep (`interfaz/alarmas/sonora.py`, `winsound`, solo Windows) corre en un hilo para no bloquear la simulación.
- Las perturbaciones se suman **al error del PID, no a la planta**.

**PID** ([control/pid.py](simulador_horno/control/pid.py)):
- `calcular_pid(error, error_prev, integral)` es **pura**. Integra con la regla del trapecio y deriva por diferencia hacia atrás. Devuelve `(u_escalado, integral, error, KD·derivada, KP·error)`.
- `actualizar_pid(error)` llama a la anterior y persiste el estado en `parametros_pid`.
- Anti-windup ([anti_windup.py](simulador_horno/control/anti_windup.py)): solo actúa si `integral > UMBRAL_INTEGRAL`. En ese caso la multiplica por `restringir_integral` (opción 5 del menú).
- Saturación ([escalado.py](simulador_horno/control/escalado.py)): `u = clamp(u_bruto / U_MAX, 0, 1)`. Un horno no enfría activamente.
- **Desempeño por defecto** (lo verifica `tests/test_control.py`): 90 % a los 58 min, sobrepaso del 0,27 %, banda de ±1 % a los 71 min y error final de 0 °C. La subida está limitada por la física (u = 1 toda la rampa), no por las ganancias.

**Actuador** ([modelo/actuador.py](simulador_horno/modelo/actuador.py)): convierte `u` en un ángulo de disparo `θ ∈ [THETA_MIN, THETA_MAX]` con un suavizado aleatorio. **No se usa** en el bucle.

## Bucle de simulación y velocidad

- [simulacion/motor.py](simulador_horno/simulacion/motor.py), clase `Motor`: la lógica pura de la corrida.
  - `__init__` reinicia el estado del PID y del impulso, recalcula B y limpia el historial.
  - `paso()` calcula el error, aplica el PID, avanza la planta, registra en el historial y suma `DT` a `t`.
  - `avanzar(n)` ejecuta n pasos. Guarda `T`, `t`, `u` y `error`.
- [simulacion/reloj.py](simulador_horno/simulacion/reloj.py): `pasos_por_refresco(factor, dt, hz, acumulado)` devuelve `N = factor/(hz·dt)`. Acumula la fracción sobrante para que x1 (2,5 pasos por refresco) también sea exacto.
- [simulacion/simulador.py](simulador_horno/simulacion/simulador.py), clase `Simulador`: el bucle visual.
  - En cada refresco (4 por segundo real) avanza N pasos del motor, actualiza la tabla y el panel y duerme el resto del periodo.
  - En modo **máxima** ejecuta lotes de `LOTE_MAXIMA` pasos durante todo el periodo y no duerme.
  - La corrida termina al **cerrar la ventana Qt** (`panel.abierta == False`) o con **Ctrl+C**.
- [historial.py](simulador_horno/simulacion/historial.py): `Historial` envuelve las listas de `parametros_horno` (comparte referencia). Guarda **una muestra cada `INTERVALO_MUESTREO` s simulados** y recorta a `MAX_MUESTRAS`, así que el arranque completo se ve a cualquier velocidad.
- El motor da ~1,3 millones de pasos por segundo real (~0,8 µs por paso). Por eso x600 es holgado y "máxima" simula decenas de horas en pocos segundos.

## Interfaz

- [app.py](simulador_horno/app.py) muestra la bienvenida y luego el bucle de menú, que despacha con el dict `ACCIONES` (`"1"`–`"7"`). `OPCION_SIMULAR = "7"` vuelve sin pausa y `OPCION_SALIR = "8"`.
- [interfaz/consola/marco.py](simulador_horno/interfaz/consola/marco.py) es el marco común de todas las pantallas (encabezado, migas, pie de atajos) y el único `Console` compartido (`marco.console`). Contiene además:
  - lectura de teclas: `leer_tecla`, que convierte Ctrl+C en `KeyboardInterrupt`;
  - el menú navegable `menu_interactivo(…, inicial=)` (flechas y Enter, teclas 1-8; Q o Esc devuelven la última opción);
  - las ayudas de formulario `pedir_float` (Enter conserva el valor actual), `confirmar` y `resumen`;
  - `panel_estado`, el resumen de la configuración que acompaña al menú, incluida la velocidad.
- [menu.py](simulador_horno/interfaz/consola/menu.py) define `ITEMS`, la lista de opciones `(clave, etiqueta, descripción)`.
- [formularios.py](simulador_horno/interfaz/consola/formularios.py) escribe directamente en los módulos de `configuracion/`. Contiene:
  - los conmutadores de perturbación (`_conmutar`);
  - `configurar_horno`, que pide `T_MAX_EQ` (no B), valida que `T_MAX_EQ > T_AMB`, `TAU > 0` y `DT > 0`, y llama a `recalcular_B`;
  - `configurar_velocidad`, un submenú con `menu_interactivo` cuyo último ítem es "Volver".
- [tabla_vivo.py](simulador_horno/interfaz/consola/tabla_vivo.py): `generar_tabla(t, T, T_set, u, error, pid, horno, acciones, velocidad, t_real)` construye el panel de rich. Muestra el reloj (tiempo simulado en hh:mm:ss, velocidad y tiempo real), las lecturas, las barras (u en [0, 1]), los términos P/I/D y la configuración.
- [interfaz/graficas/panel.py](simulador_horno/interfaz/graficas/panel.py): `PanelGraficas` es una única ventana `GraphicsLayoutWidget`.
  - Tiene cuatro vistas: temperatura frente al tiempo con la línea del setpoint, error frente al tiempo, el corte del horno coloreado por T (colorimetría) y la franja histórica de color, más una barra de escala en °C.
  - **El eje de tiempo está en minutos simulados.** La franja lee del historial, igual que las curvas.
  - Su API es `actualizar(tiempos, temps, errs, T, T_set)` (tiempos en segundos), `abierta` y `cerrar()`.
  - El modelo es **síncrono**: cada `actualizar` llama a `app.processEvents()`, sin hilos ni `QTimer`.

## Pruebas

`tests/` usa pytest (configurado en `pytest.ini`, con `pythonpath = .`). Las pruebas no importan rich ni Qt. El fixture `configuracion_limpia` de [conftest.py](tests/conftest.py) guarda y restaura los módulos de configuración en cada prueba: las listas se restauran en sitio porque `Historial` comparte la referencia.

| Archivo | Comprueba |
|---|---|
| `test_fisica.py` | u = 1 converge a `T_MAX_EQ`; B se recalcula al cambiar T_AMB, TAU o T_MAX_EQ |
| `test_control.py` | u ∈ [0, 1] en 4 h (con y sin perturbaciones); métricas de la corrida por defecto (sobrepaso < 5 %) |
| `test_velocidad.py` | simulado/real = factor para cada velocidad y varios DT, sin `time.sleep` |
| `test_historial.py` | conserva ≥ 4 h; una muestra por segundo simulado sea cual sea DT |
| `test_perturbaciones.py` | la tasa de impulsos no cambia con DT (semilla fija); el signo es constante en el impulso y alterna entre impulsos |
| `test_capas.py` | `motor` y `reloj` no importan rich, PySide6 ni pyqtgraph |

## Cómo añadir cosas

- **Nueva opción de menú:** añade una tupla en `menu.ITEMS`, la función en `formularios.py` y la entrada en `app.ACCIONES`. Si cambia el número de opciones, revisa `ATAJOS_MENU` en `marco.py`, `OPCION_SIMULAR` y `OPCION_SALIR` en `app.py` y la tabla de controles del README.
- **Nuevo parámetro editable:** añádelo como variable de módulo en `configuracion/parametros_*.py`, pídelo en el formulario correspondiente, muéstralo en `marco.panel_estado` y en `tabla_vivo`, y añade su módulo a `_MODULOS` en `tests/conftest.py` si es un archivo nuevo.
- **Constante interna:** `configuracion/limites.py`. **Colores y estilos:** `estilos/tema.py`.
- **Nueva velocidad:** basta con añadirla a `limites.VELOCIDADES` y a `_DESCRIPCION_VELOCIDAD` en `formularios.py`.
- **Cambiar de integrador** (Euler por Heun o RK4): sustituye el import de `simular_horno` en `simulacion/motor.py` o hazlo seleccionable desde el menú.
- **Para acelerar, nunca agrandes `DT`:** cambia la velocidad. `DT` es un parámetro numérico.
- **Nueva dependencia:** fija la versión en `requirements.txt`. Si PyInstaller no la detecta, añádela a `hiddenimports` o `datas` en `main.spec`. Por ejemplo, `readchar` necesita `copy_metadata` y `pyqtgraph` necesita `collect_data_files`.
- Ejecuta `python -m pytest` antes de cada commit.

## Deuda técnica y trampas conocidas

1. Las perturbaciones afectan al **error**, no a la física. `delta_T` se calcula pero `simular_horno` no lo usa.
2. **El anti-windup es asimétrico y limita la sintonía.** No se acota la integral negativa, y la positiva queda topada en ~`UMBRAL_INTEGRAL`. En el equilibrio el horno necesita u ≈ 0,76, es decir `KI·integral/U_MAX ≈ 0,76`. Si KI es bajo, la integral necesaria supera el tope y queda **error permanente**. Con KP = 200, tras 6 h quedan 2,4 °C con KI = 8, 11 °C con KI = 7 y 28 °C con KI = 5.
3. El estado del impulso vive en atributos de la función `impulso_probabilistico` (se reinicia con `reiniciar_impulso()`). Debería ser un objeto.
4. `senal_error.py` (capa de control) importa `interfaz.alarmas.sonora`. Es una violación de capas pendiente: debería notificar la simulación.
5. En el primer paso `error_prev = 0`, lo que produce un *derivative kick* (`KD·error/DT`). Es inofensivo porque u ya satura en 1 al inicio.
6. `numerico/integradores.py` y `modelo/actuador.py` existen pero no están conectados, así que PyInstaller no los incluye en el exe.
7. El README menciona la Ley de Fourier, pero el modelo solo tiene pérdidas tipo Newton más la entrada de control.
8. **Modo "máxima":** simula ~70 h en 3 s reales. Con un historial de 5 h, a los pocos segundos ya no se ve el arranque.

## Archivos fuera del paquete

- `main.spec`: configuración de PyInstaller (onefile, consola). Excluye matplotlib, tkinter y PyQt5/6.
- `requirements.txt`: dependencias de ejecución. `requirements-dev.txt`: PyInstaller, pytest y sus dependencias.
- `pytest.ini` y `tests/`: pruebas automáticas.
- `build/` y `dist/`: artefactos generados, ignorados por git.
- `README.md`: documentación para el usuario final, con datos de contacto del autor.
