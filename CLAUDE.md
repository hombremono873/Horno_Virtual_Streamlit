# CLAUDE.md

Guía para entender y modificar este código. Léela antes de tocar nada.

## Qué es

Simulador de consola del **calentamiento de un horno eléctrico regulado por un controlador PID**. Es un trabajo académico de *Métodos Numéricos* (Universidad de Antioquia; autor Omar Alberto Torres, docente Yony Ceballos). La planta es un horno: no hay motor ni otro actuador mecánico.

El usuario configura el PID y el horno desde un menú de consola (`rich` + `readchar`) y lanza una simulación en tiempo real. La corrida muestra a la vez una tabla viva en la consola y una ventana Qt (`pyqtgraph` + `PySide6`) con las curvas de temperatura y error y la "colorimetría" térmica del horno.

Todos los identificadores, comentarios y textos de interfaz están en **español**. Mantén esa convención.

## Comandos

Todo se ejecuta **desde la carpeta `simulador/`**: `main.py` importa el paquete `simulador_horno` de forma relativa al CWD.

```bash
# Entorno (Windows, Python 3.13)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt                          # solo ejecución
pip install -r requirements.txt -r requirements-dev.txt  # + PyInstaller

# Ejecutar
python main.py

# Regenerar el ejecutable dist/main.exe (onefile, ~62 MB). NO se regenera solo.
pyinstaller main.spec --noconfirm --clean
```

- **Requiere escritorio (Qt).** Sin pantalla, usa `QT_QPA_PLATFORM=offscreen` (útil para pruebas automáticas del bucle).
- El menú necesita una terminal real: `readchar` lee teclas sin Enter.
- No hay tests automatizados ni linter configurado.
- Si `.venv` falla al activarse (rutas viejas incrustadas tras copiar la carpeta), recréalo con `python -m venv .venv --clear` y reinstala.

## Arquitectura

Cada carpeta de `simulador_horno/` responde a una pregunta:

```
simulador_horno/
├── app.py            # arranque: bienvenida + bucle del menú
├── configuracion/    # ¿con qué parámetros?   parametros_horno, parametros_pid, parametros_electricos, limites
├── modelo/           # ¿qué se simula?        horno (ecuación + Euler), perturbaciones, actuador
├── control/          # ¿quién controla?       pid, anti_windup, escalado, senal_error
├── numerico/         # ¿con qué método?       integradores (Heun, RK4)
├── simulacion/       # ¿quién coordina?       simulador (bucle), historial
├── interfaz/         # ¿qué ve el usuario?    consola/, graficas/, alarmas/
└── estilos/          # ¿cómo se ve?           tema (paleta y medidas)
```

Flujo de ejecución:

```
main.py  ->  simulador_horno/app.py::ejecutar()
                 │
                 ├── interfaz/consola   (menú, formularios)  ──escribe──►  configuracion/*
                 │
                 └── simulacion/Simulador.ejecutar()
                        │  en cada paso:
                        ├─► control/senal_error.construir_error(t, T)
                        ├─► control/pid.actualizar_pid(error)  -> u ∈ [-1, 1]
                        ├─► modelo/horno.simular_horno(T, u)  (Euler)
                        ├─► simulacion/historial.Historial.registrar(...)
                        ├─► interfaz/consola/tabla_vivo.generar_tabla(...)  (rich.Live)
                        └─► interfaz/graficas/panel.PanelGraficas.actualizar(...)
```

| Capa | Ruta | Responsabilidad | Regla |
|---|---|---|---|
| Configuración | `configuracion/` | Parámetros y estado global | Sin lógica |
| Modelo | `modelo/` | Ecuación del horno, perturbaciones, actuador | **Sin E/S** |
| Control | `control/` | PID, anti-windup, saturación, señal de error | **Sin E/S** (excepción: ver la deuda técnica, punto 4) |
| Numérico | `numerico/` | Métodos de integración alternativos | **Sin E/S** |
| Simulación | `simulacion/` | Bucle de la corrida e historial | Orquesta modelo, control e interfaz |
| Interfaz | `interfaz/` | Consola rich, ventana Qt, beep | Sin cálculo de control |
| Estilos | `estilos/` | Paleta y medidas visuales | Solo constantes |

### Estado global: módulos de `configuracion/` como variables mutables

Este punto es el más importante para entender el código. **No hay objetos de configuración.** El estado vive en variables de módulo que se importan con alias y se mutan en caliente:

- `configuracion/parametros_horno.py` (alias habitual `var`, `vhorno`, `horno`): `T_AMB=30`, `T_SET=1000`, `B=100`, `TAU=3000`, `DT=0.1`. También guarda las listas del historial (`tiempos`, `temperaturas`, `errores`) y los flags de perturbación (`error_oscilante`, `flag_error`, `delta_T`).
- `configuracion/parametros_pid.py` (alias `var`, `vpid`, `pid`): `KP=35`, `KI=10`, `KD=2`, `restringir_integral=0.85` y el estado interno del PID entre pasos (`error_prev`, `integral`, `derivada`, `proporcional`).
- `configuracion/parametros_electricos.py`: `angulo_conduccion` (no se usa en el bucle).
- `configuracion/limites.py`: constantes **fijas** que el menú no edita: `U_MAX=20000`, `UMBRAL_INTEGRAL=2000`, `MAX_MUESTRAS=5000`, `REFRESCO_HZ=4`, `TEMP_MIN_COLOR=30` y `TEMP_MAX_COLOR=1200` (rango del mapa de color), `THETA_MIN=10` y `THETA_MAX=170`.
- `estilos/tema.py`: paleta y medidas compartidas por la consola (estilos rich `C_*`) y las gráficas (colores hex `G_*`, colormap `plasma`, tamaño de ventana).

Siempre importa el **módulo** (`from simulador_horno.configuracion import parametros_horno as vhorno`) y lee `vhorno.T_SET` en el momento de usarlo. Nunca hagas `from ...parametros_horno import T_SET`: copiarías el valor y no verías los cambios del menú.

## Modelo numérico

**Planta** ([modelo/horno.py](simulador_horno/modelo/horno.py)): sistema de primer orden

```
dT/dt = (1/TAU)·(T_AMB − T) + B·u
T[k+1] = T[k] + DT·dT/dt          (Euler explícito)
```

Protege contra `TAU == 0` y contra resultados NaN o infinitos (devuelve `T_actual`). [integradores.py](simulador_horno/numerico/integradores.py) contiene la misma ecuación con Heun (RK2) y RK4 (`simular_horno_heun` y `simular_horno_runge`), pero **no están conectados** al bucle ni al menú.

**Error** ([control/senal_error.py](simulador_horno/control/senal_error.py)): `error = T_SET − T`, más perturbaciones opcionales:
- `error_oscilante` (opción 3 del menú): `get_ruido(t) = 20·sin(0.05·t) + U(−0.5, 1.5)`.
- `flag_error` (opción 4): `perturbacion_total(t, prob=0.02, dur=3, mag=80)`, que suma ruido, senoide y un impulso probabilístico de signo alternante. Cada impulso dispara un beep (`interfaz/alarmas/sonora.py`, `winsound`, solo en Windows).
- Las perturbaciones se suman **al error del PID, no a la planta**.

**PID** ([control/pid.py](simulador_horno/control/pid.py)):
- `calcular_pid(error, error_prev, integral)` es **pura**. Integra con la regla del trapecio y deriva por diferencia hacia atrás. Devuelve `(u_escalado, integral, error, KD·derivada, KP·error)`.
- `actualizar_pid(error)` llama a la anterior y persiste el estado en `parametros_pid`.
- Anti-windup ([anti_windup.py](simulador_horno/control/anti_windup.py)): solo actúa si `integral > UMBRAL_INTEGRAL`. En ese caso la multiplica por `restringir_integral` (opción 5 del menú).
- Saturación ([escalado.py](simulador_horno/control/escalado.py)): `u = clamp(u_bruto / U_MAX, −1, 1)`.

**Actuador** ([modelo/actuador.py](simulador_horno/modelo/actuador.py)): convierte `u` en un ángulo de disparo `θ ∈ [THETA_MIN, THETA_MAX]` con un suavizado aleatorio. **No se usa** en el bucle.

## Bucle de simulación

[simulacion/simulador.py](simulador_horno/simulacion/simulador.py), clase `Simulador`:
- `paso()` calcula el error, aplica el PID, avanza la planta, registra en el historial y suma `DT` a `t`.
- `ejecutar()` abre `PanelGraficas`, entra en `rich.Live(screen=True)` y repite `paso`, refresco de la tabla, `panel.actualizar(...)` y `_dormir_resto`.
- **Tiempo real acoplado:** `_dormir_resto` duerme hasta completar `DT` segundos reales por paso, así que `DT` es a la vez el paso de integración y el periodo de reloj.
- La corrida termina al **cerrar la ventana Qt** (`panel.abierta == False`) o con **Ctrl+C**. `_finalizar` cierra el panel y limpia el historial.
- [historial.py](simulador_horno/simulacion/historial.py): `Historial` envuelve las listas de `parametros_horno` (comparte referencia) y recorta a `MAX_MUESTRAS`.

## Interfaz

- [app.py](simulador_horno/app.py) muestra la bienvenida y luego el bucle de menú, que despacha con el dict `ACCIONES` (`"1"`–`"6"`). La opción `"7"` sale.
- [interfaz/consola/marco.py](simulador_horno/interfaz/consola/marco.py) es el marco común de todas las pantallas (encabezado, migas, pie de atajos) y el único `Console` compartido (`marco.console`). Contiene además:
  - lectura de teclas: `leer_tecla`, que convierte Ctrl+C en `KeyboardInterrupt`;
  - el menú navegable `menu_interactivo` (flechas y Enter, teclas 1-7; Q o Esc devuelven la última opción);
  - las ayudas de formulario `pedir_float` (Enter conserva el valor actual), `confirmar` y `resumen`;
  - `panel_estado`, el resumen de la configuración que acompaña al menú.
- [menu.py](simulador_horno/interfaz/consola/menu.py) define `ITEMS`, la lista de opciones `(clave, etiqueta, descripción)`.
- [formularios.py](simulador_horno/interfaz/consola/formularios.py) escribe directamente en los módulos de `configuracion/`. También contiene los conmutadores de perturbación (`_conmutar`).
- [tabla_vivo.py](simulador_horno/interfaz/consola/tabla_vivo.py): `generar_tabla(t, T, T_set, u, error, pid, horno, acciones)` construye el panel de rich que se ve durante la corrida.
- [interfaz/graficas/panel.py](simulador_horno/interfaz/graficas/panel.py): `PanelGraficas` es una única ventana `GraphicsLayoutWidget` con cuatro vistas: temperatura frente al tiempo con la línea del setpoint, error frente al tiempo, el corte del horno coloreado por T (colorimetría) y la franja histórica de color, más una barra de escala en °C. Su API es `actualizar(tiempos, temps, errs, T, T_set)`, `abierta` y `cerrar()`. El modelo es **síncrono**: cada `actualizar` llama a `app.processEvents()`, sin hilos ni `QTimer`.

## Cómo añadir cosas

- **Nueva opción de menú:** añade una tupla en `menu.ITEMS`, la función en `formularios.py` y la entrada en `app.ACCIONES`. Si cambia el número de opciones, revisa `ATAJOS_MENU` en `marco.py` y el `"7"` de salida en `app.py`.
- **Nuevo parámetro editable:** añádelo como variable de módulo en `configuracion/parametros_*.py`, pídelo en el formulario correspondiente y muéstralo en `marco.panel_estado` y en `tabla_vivo`.
- **Constante interna:** `configuracion/limites.py`. **Colores y estilos:** `estilos/tema.py`.
- **Cambiar de integrador** (Euler por Heun o RK4): sustituye el import de `simular_horno` en `simulacion/simulador.py` o hazlo seleccionable desde el menú.
- **Nueva dependencia:** fija la versión en `requirements.txt`. Si PyInstaller no la detecta, añádela a `hiddenimports` o `datas` en `main.spec`. Por ejemplo, `readchar` necesita `copy_metadata` y `pyqtgraph` necesita `collect_data_files`.
- Conserva la **equivalencia numérica**: con perturbaciones desactivadas el resultado es determinista, así que cualquier refactor debe producir la misma serie de T.

## Deuda técnica y trampas conocidas

1. Las perturbaciones afectan al **error**, no a la física. `delta_T` se calcula pero `simular_horno` no lo usa.
2. El anti-windup es **asimétrico**: no se acota la integral negativa.
3. **El estado del PID no se reinicia entre corridas.** `Simulador.__init__` no pone a cero `parametros_pid.integral` ni `error_prev`, así que la segunda simulación arranca con la integral de la anterior. El estado del impulso (atributos de la función `impulso_probabilistico`) también persiste.
4. `senal_error.py` (capa de control) importa `interfaz.alarmas.sonora`. Es una violación de capas pendiente: debería notificar la simulación.
5. En el primer paso `error_prev = 0`, lo que produce un *derivative kick* (`KD·error/DT`). Con los valores por defecto el PID satura en `u = 1` al inicio. Es esperable: el usuario debe sintonizar.
6. `numerico/integradores.py` y `modelo/actuador.py` existen pero no están conectados.
7. El README menciona la Ley de Fourier, pero el modelo solo tiene pérdidas tipo Newton más la entrada de control.

## Archivos fuera del paquete

- `main.spec`: configuración de PyInstaller (onefile, consola). Excluye matplotlib, tkinter y PyQt5/6.
- `requirements.txt`: dependencias de ejecución. `requirements-dev.txt`: PyInstaller y sus dependencias.
- `build/` y `dist/`: artefactos generados, ignorados por git.
- `README.md`: documentación para el usuario final, con datos de contacto del autor.
