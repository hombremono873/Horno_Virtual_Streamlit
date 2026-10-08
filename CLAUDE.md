# CLAUDE.md

Guía técnica compacta. El detalle de cada módulo está en sus docstrings; aquí va lo que **no** se deduce leyendo un archivo suelto.

## Qué es
Simulador **pedagógico** de un horno eléctrico con control PID (Métodos Numéricos, UdeA; autor Omar Alberto Torres). Tiene un menú de consola (`rich` + `readchar`) y un monitor Qt (`pyqtgraph` + `PySide6`). Todo el código, los comentarios y los textos están en **español**: mantén esa convención. El README es la guía para el usuario.

## Comandos (desde `simulador/`, porque `main.py` importa el paquete relativo al CWD)
```bash
.venv\Scripts\python main.py                       # ejecutar
.venv\Scripts\python -m pytest                     # 125 pruebas, ~5 s, sin pantalla (-s muestra métricas)
.venv\Scripts\pyinstaller main.spec --noconfirm --clean   # dist/main.exe (~64 MB); NO se regenera solo
```
- **`main.exe` abierto bloquea la compilación:** el exe queda con la fecha anterior aunque el build diga "complete". Verifica la fecha de `dist/main.exe` y que no haya procesos `main`.
- Sin pantalla: `QT_QPA_PLATFORM=offscreen`; para capturas con texto añade `QT_QPA_FONTDIR=C:/Windows/Fonts`. El menú necesita una terminal real (`readchar`).
- Si `.venv` falla tras copiar la carpeta: `python -m venv .venv --clear` y reinstala los `requirements*.txt`.

## Mapa
```
simulador_horno/
├── app.py           menú: dict ACCIONES "1"–"8"; OPCION_SIMULAR="8" (sin pausa), OPCION_SALIR="9"
├── configuracion/   ESTADO GLOBAL mutable: parametros_horno, parametros_pid, parametros_simulacion; limites (constantes)
├── modelo/          horno.simular_horno (Euler), perturbaciones (impulso por tasa/hora), actuador (sin conectar)
├── control/         pid, anti_windup (ninguno|recorte|condicional), escalado (u∈[0,1]), senal_error
├── numerico/        integradores (METODOS/NOMBRES/ORDEN/EVALUACIONES), comparacion (vs. exacta), estabilidad (R(z))
├── simulacion/      motor (paso, sin E/S), reloj (pasos por refresco, pasos_restantes), historial,
│                    metricas, resultados (CSV), simulador (bucle visual)
├── interfaz/        consola/ (marco, menu, formularios, tabla_vivo, comparacion, estabilidad, metricas, dashboard),
│                    graficas/ (panel = monitor; comparacion, estabilidad y dashboard = ventanas estáticas), alarmas/
└── estilos/tema.py  colores y medidas de la consola (C_*) y de las gráficas (G_*)
```
Flujo de una corrida: `Simulador.ejecutar` → por cada refresco (4 Hz reales) `reloj.pasos_por_refresco` → `Motor.avanzar(N)` → (`construir_error` → `actualizar_pid` → **registrar** → `METODOS[metodo]`) → `tabla_vivo` + `panel.actualizar` → al salir: métricas, CSV y espera de una tecla.

## Estado global: lo más importante
No hay objetos de configuración: los parámetros son variables de módulo que el menú **muta en caliente**. Importa siempre el módulo (`from simulador_horno.configuracion import parametros_horno as vhorno`) y lee `vhorno.X` al usarlo; **nunca** `from ... import X`. Las listas del historial viven en `parametros_horno` (`tiempos`, `temperaturas`, `errores`, `potencias`) y `Historial` las comparte por referencia. `tests/conftest.py` guarda y restaura estos módulos en cada prueba (las listas, en sitio). Si añades un módulo `parametros_*`, inclúyelo en `_MODULOS`.

## Decisiones y trampas (no las rompas sin querer)
- **Una sola ecuación:** `modelo.horno.derivada(T, u)` la usan Euler, Heun y RK4. Las perturbaciones del horno entran por `horno.entorno = (T_amb, perdida_extra, potencia)`, que el `Motor` fija **solo durante el paso** y restaura a `ENTORNO_IDEAL` en un `finally`. Con el entorno ideal el resultado es bit a bit el de la fórmula original (verificado con huellas).
- **Física:** `B = (T_MAX_EQ − T_AMB)/TAU` es derivada. Llama a `recalcular_B()` tras cambiar `T_AMB`, `TAU` o `T_MAX_EQ`. `u ∈ [0, 1]`. `T_INICIAL` es la temperatura de arranque (= `T_AMB`, en frío).
- **Velocidad ≠ física:** acelerar nunca cambia `DT`. N = factor/(HZ·DT), con la fracción acumulada. La duración se respeta con `pasos_restantes`, también en "máxima". Al terminar, el bucle **sigue refrescando sin avanzar** para que el monitor responda.
- **`Motor` es puro** (sin rich ni Qt; lo verifica `test_capas`). Reinicia el estado del PID y del impulso en cada corrida, y **registra antes de integrar**, de modo que cada muestra `(t, T, error, u)` es del mismo instante.
- **Los integradores leen `vhorno.DT`.** `comparacion.integrar` lo cambia temporalmente y lo restaura en un `finally`.
- **PID:** la derivada va sobre la **medición** (`−Δmedida/DT`, `medida = T_SET − error`; vale 0 en el primer paso). Anti-windup por defecto **condicional** (no integra si `u_bruta > 1` con error positivo, ni si `u_bruta < 0` con error negativo). El modo **recorte** reproduce bit a bit el original y con KI bajo deja error permanente (documentado y probado).
- **Perturbaciones** (`limites.PERTURBACIONES`: atributo, nombre, tipo; opción 3 con submenú de conmutadores):
  - sobre la **medición** (se suman al error): `error_oscilante`, `flag_error` (impulsos) y `ruido_termopar` (gauss σ = 1 °C);
  - sobre el **horno** (vía `entorno`): `puerta` (`EventoAleatorio`, pérdida extra 1/`TAU_PUERTA`), `red_variable` (potencia = (V/Vn)²) y `ambiente_variable`.
  - Los contadores `Motor.impulsos` y `Motor.aperturas` van al CSV. El impulso se define por tasa por hora simulada (`p = 1 − e^(−tasa·DT/3600)`) y tiene signo constante durante cada impulso. `construir_error` devuelve `(error, impulso_nuevo)`; el `Motor` solo **cuenta** los impulsos (`impulsos`, `impulso_activo`), y el `Simulador` (interfaz) pita una vez por refresco con impulsos nuevos y muestra "⚡ IMPULSO" en la tabla. La lógica no importa la interfaz (`test_capas`).
- **Métricas:** se calculan sobre la temperatura **real** y valen también para arranques por encima del setpoint. IAE/ISE solo son comparables entre corridas de igual duración.
- **CSV:** `resultados/` junto al exe (`sys.frozen`) o en el CWD. UTF-8 con BOM, `;` y coma decimal (Excel es-CO); cabecera `# clave;valor`; columnas `t_s;T_C;T_set_C;error_C;u`. `resultados.leer()`, `listar()` (más reciente primero) y `metricas_guardadas()` alimentan el **dashboard** (opción 4): elige entre las 7 corridas más recientes y muestra `tabla_comparativa` (rich) y `VentanaDashboard` (curvas superpuestas, con zoom permitido).
- **Monitor (`panel.py`):**
  - sin ratón: la rueda congelaba la vista;
  - eje Y **centrado en el setpoint**, con semirango tomado de los últimos 30 min;
  - eje X en minutos y `[0, duración]`;
  - `setImage` **antes** de `setRect` en la franja;
  - ejes Y del mismo ancho (64), porque si no, el enlace del eje X oculta el inicio del error;
  - es síncrono: `processEvents` en cada `actualizar`.
- **Ventanas estáticas** (comparación, estabilidad): `app.exec()` bloquea hasta que se cierran y conviven con el monitor en la misma sesión.
- **Submenús con `menu_interactivo`:** Esc o Q devuelven el **último** ítem, así que el último debe ser "Volver" o "Conservar".

## Cómo añadir
- **Opción de menú:** `menu.ITEMS` + función en `formularios.py` + `app.ACCIONES`; revisa `ATAJOS_MENU` ("1-9"). El menú no admite más de 9 teclas: amplía mejor con submenús.
- **Parámetro editable:** variable en `configuracion/parametros_*.py`, formulario, `marco.panel_estado`, `tabla_vivo`, `Simulador._parametros_corrida` (CSV) y `conftest`.
- **Método numérico:** función `(T, u) -> T_nuevo` en `integradores.py` + `METODOS`, `NOMBRES`, `ORDEN`, `EVALUACIONES` + `_COEFICIENTES` en `estabilidad.py` + `_DESCRIPCION_METODO`.
- **Dependencia:** fija la versión en `requirements.txt`. Si PyInstaller no la detecta, añádela a `main.spec` (`hiddenimports` o `datas`; `readchar` usa `copy_metadata` y `pyqtgraph` `collect_data_files`).

## Pruebas (`tests/`, `pytest.ini` con `pythonpath = .`)
GitHub Actions (`.github/workflows/pruebas.yml`) las corre en cada push (Windows, Python 3.13, `QT_QPA_PLATFORM=offscreen`). Las pruebas nuevas no deben necesitar pantalla ni escribir fuera de `tmp_path`.

física · perturbaciones del horno · dashboard · control (métricas por defecto: sobrepaso 0,54 %, t90 58 min, establecimiento 71 min) · velocidad · duración (bucle real de `Simulador`) · historial · perturbaciones (tasa independiente de DT) · integradores y comparación (orden 1/2/4) · estabilidad (límites 2τ y 2,785τ; el código amplifica exactamente por R) · anti_windup · derivada · métricas (contra fórmulas de primer orden) · resultados (ida y vuelta del CSV) · arranque · panel (Qt offscreen) · capas.

## Deuda técnica conocida
1. El estado del impulso vive en atributos de la función `impulso_probabilistico` (`reiniciar_impulso()`).
2. El trapecio del primer paso usa `error_prev = 0` (efecto despreciable).
3. `modelo/actuador.py` no está conectado, así que no entra en el exe.
4. Con la física actual el sobrepaso máximo alcanzable es ~2 %. Un sobrepaso "de libro" requiere margen de potencia y retardo del termopar (pendiente; ver la memoria del proyecto).
