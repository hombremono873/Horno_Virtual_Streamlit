# CLAUDE.md

Guía técnica compacta. El detalle de cada módulo está en sus docstrings; aquí va lo que **no** se deduce leyendo un archivo suelto.

## Qué es
Simulador **pedagógico** de un horno eléctrico con control PID (Métodos Numéricos, UdeA; autor Omar Alberto Torres). **Este repositorio es solo WEB (Streamlit)**: la versión de escritorio (rich, Qt, `main.exe`) vive en `Hornovirtual_2026` y aquí no se mantiene. Código, comentarios y textos en **español**. El README es la guía para el estudiante. Plan y estado: `documentos/traspaso_version_streamlit.md` y `documentos/prompt_migracion_streamlit.txt` (las tres fases hechas; falta publicar).

## Comandos (desde `simulador/`)
```bash
.venv\Scripts\python -m pytest                    # 190 pruebas, ~20 s (-s muestra métricas)
.venv\Scripts\python -m streamlit run streamlit_app.py   # http://localhost:8501
```
- El usuario levanta la app con `iniciar_web.bat` (usa `.venv` explícito): su perfil de PowerShell tiene un `activate` que activa el entorno de otro proyecto (`usersdj`), así que nunca le des comandos con `python` a secas. `.vscode/settings.json` (en la carpeta de arriba, fuera del repo) apunta las terminales a `simulador\.venv`.
- Si levantas Streamlit para comprobar algo, ciérralo al terminar. `AppTest` (tests/test_app.py) prueba la página sin servidor.
- El `python` del PATH es 3.8: crea el venv con `C:\Users\usuario\AppData\Local\Programs\Python\Python313\python.exe -m venv .venv --clear`. El servidor Black de VS Code bloquea `.venv\Scripts\python.exe` al recrearlo.
- CI: `.github/workflows/pruebas.yml` (Ubuntu, Python 3.13, como Streamlit Community Cloud).

## Mapa
```
simulador_horno/
├── configuracion/  parametros (dataclasses: ParametrosHorno, ParametrosPID, Perturbaciones,
│                   ParametrosSimulacion → Configuracion), limites (constantes no editables)
├── modelo/         horno (derivada, Euler), perturbaciones (Impulso, EventoAleatorio, Perturbador), actuador (sin conectar)
├── control/        pid (calcular_pid puro + clase PID), anti_windup, escalado (u∈[0,1]), senal_error
├── numerico/       integradores (METODOS/NOMBRES/ORDEN/EVALUACIONES), comparacion (vs. exacta), estabilidad (R(z))
├── simulacion/     simulador (Simulador: una corrida, sin E/S), reloj, historial, metricas, resultados (CSV)
├── web/            datos (diezmado, CSV), graficas (plantilla y figura Plotly), ejecucion (modo en vivo),
│                   app (página Streamlit); streamlit_app.py en la raíz solo llama a app.main()
└── estilos/tema.py paleta de las gráficas (G_*); .streamlit/config.toml repite fondo, panel y texto (probado)
```
Un paso: `Simulador.paso` → `construir_error` → `PID.paso` → **registrar** → `Perturbador.entorno` → `METODOS[metodo](T, u, horno, entorno)`.

## Estado: sin globales
- Cada `Simulador(config, semilla)` tiene su `Configuracion`, `PID`, `Perturbador` (`random.Random(semilla)`) e `Historial`. Dos simuladores no comparten nada (`test_independencia`, también en hilos). **No vuelvas a meter estado a nivel de módulo.**
- La configuración se lee en **cada paso** (cambiar T_SET o KP afecta a la corrida en curso); `metodo` y `duracion` se fijan en `reiniciar()`. Modifica los campos en sitio, no reemplaces `config.pid` etc. (el PID guarda la referencia; `reiniciar` la reengancha).
- `reiniciar()` repite la corrida con la misma semilla; `semilla=None` = corrida distinta cada vez.
- El núcleo no importa ninguna interfaz (`test_capas`: ni `simulador_horno.web`, streamlit, plotly, pandas, rich ni Qt). Solo `web/` las usa.

## Decisiones y trampas (no las rompas sin querer)
- **No regresión** (`tests/test_no_regresion.py`, `tests/referencias/*.json`): huellas SHA-256 de `(t, T, error, u)` de 9 escenarios generadas ANTES de encapsular; deben coincidir **bit a bit**, también con perturbaciones. Para ello, conserva el **orden en que se consume el generador**: medición (gauss del termopar → uniform oscilante → uniform + random del impulso) y luego la puerta. Regenerar solo si el cambio de resultados es intencional (`REGENERAR_REFERENCIAS=1`).
- **Una sola ecuación:** `modelo.horno.derivada(T, u, horno, entorno)` la usan los tres métodos. Con `ENTORNO_IDEAL` es bit a bit la fórmula original.
- **Física:** `B` es propiedad derivada de `ParametrosHorno` (`(T_MAX_EQ − T_AMB)/TAU`). `u ∈ [0, 1]`. `T_INICIAL` = arranque (= `T_AMB`, en frío). ~700 mil pasos/s (B se recalcula en cada evaluación; no lo caches sin invalidarlo).
- **Velocidad ≠ física:** nunca cambia `DT`. N = factor/(HZ·DT) con fracción acumulada (`reloj.pasos_por_refresco`). La duración se respeta con `avanzar_sin_pasarse` / `completar`; `avanzar(n)` no mira la duración.
- **Registrar antes de integrar:** cada muestra `(t, T, error, u)` es del mismo instante.
- `comparacion.integrar` y `estabilidad.estudiar` trabajan sobre una **copia** del horno (`dataclasses.replace`), nunca lo modifican.
- **PID:** derivada sobre la **medición** (`−Δmedida/DT`, 0 en el primer paso). Anti-windup por defecto **condicional**; durante la subida saturada la integral queda en 0. **Recorte** reproduce el original y con KI bajo deja error permanente (probado).
- **Perturbaciones** (`limites.PERTURBACIONES`: atributo, nombre, tipo): medición (`error_oscilante`, `flag_error`, `ruido_termopar`, se suman al error) y horno (`puerta`, `red_variable`, `ambiente_variable`, vía `entorno`). Eventos por tasa/hora simulada (`p = 1 − e^(−tasa·DT/3600)`). El simulador solo **cuenta** impulsos y aperturas (`impulsos`, `aperturas`, `impulso_activo`, `puerta_abierta`); avisar es cosa de la interfaz.
- **Métricas** sobre la temperatura **real**; IAE/ISE solo comparables con igual duración.
- **CSV web** (`web.datos.csv`, decisión del usuario): estándar, `,` y punto decimal, UTF-8, en memoria; columnas `t_s,T,T_set,error,u,P,I,D,perturbacion,T_medida`. `P, I, D` normalizados (`P+I+D` = u sin saturar); `perturbacion = error − (T_set − T)`. El `Historial` guarda `setpoints` (el setpoint puede cambiar en vivo) y los tres términos.
- **CSV de disco** (`simulacion.resultados`, herencia del escritorio): `;` y coma decimal; la web no lo usa (solo lo prueba `test_resultados`/`test_dashboard`).
- **Web:** un `Simulador` + `EjecucionEnVivo` por sesión en `st.session_state`. Los widgets (claves `w_*`) se copian a `sim.config` en cada ejecución (`_aplicar_widgets`, también al inicio de cada callback de botón). En vivo: `st.fragment(run_every=1/REFRESCO_HZ)` solo mientras `en_vivo`; al terminar la corrida hace `st.rerun()` para parar el temporizador. `EjecucionEnVivo` calcula los pasos con el tiempo REAL entre refrescos (tope 1 s; la pausa no se recupera). Plotly con `theme=None` (usa la plantilla propia) y `uirevision` para conservar el zoom. Usa `width="stretch"`, no `use_container_width` (en desuso).

## Cómo añadir
- **Parámetro editable:** campo en la dataclass de `configuracion/parametros.py`; si va al CSV, `Simulador.parametros_corrida`.
- **Método numérico:** función `(T, u, horno, entorno=ENTORNO_IDEAL) -> T_nuevo` en `integradores.py` + `METODOS`, `NOMBRES`, `ORDEN`, `EVALUACIONES` + `_COEFICIENTES` en `estabilidad.py`.
- **Perturbación aleatoria:** usa `Perturbador.rng` (nunca el módulo `random`) y añádela al final del orden de consumo para no romper las referencias.
- **Control en la barra lateral:** widget con clave `w_<campo>` en `web/app._barra_lateral` + línea en `_aplicar_widgets`; prueba con `AppTest` en `tests/test_app.py`.
- **Dependencia:** fija la versión en `requirements.txt` (lo instala Streamlit Community Cloud).

## Pruebas (`tests/`, `pytest.ini` con `pythonpath = .`)
No necesitan pantalla ni escriben fuera de `tmp_path`. Cubren: no regresión · independencia · física · perturbaciones (semilla, tasa independiente de DT) · perturbaciones del horno · control (sobrepaso 0,54 %, t90 58 min, establecimiento 71 min) · velocidad · duración · historial · integradores y comparación (orden 1/2/4) · estabilidad (2τ y 2,785τ) · anti-windup · derivada · métricas · resultados y lectura de corridas · arranque · capas · web (diezmado, CSV, figura, modo en vivo con reloj falso, tema) · app (AppTest: carga, corrida completa, CSV, widgets, superposición, semilla, en vivo, dos sesiones).

## Deuda técnica conocida
1. El trapecio del primer paso usa `error_prev = 0` (efecto despreciable).
2. `modelo/actuador.py` no está conectado.
3. Con la física actual el sobrepaso máximo es ~2 %; uno "de libro" requiere margen de potencia y retardo del termopar (pendiente, ver traspaso §6).
4. `simulacion.resultados` (CSV en disco, `sys.frozen`) es herencia del escritorio y la web no lo usa; podría retirarse.
5. Ideas para la web (no hechas): vistas de comparación de métodos y estabilidad (`numerico.comparacion`/`estabilidad` ya dan los datos), dashboard de varias corridas de la sesión, sintonía asistida.
