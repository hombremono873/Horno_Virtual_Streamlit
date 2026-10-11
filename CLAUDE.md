# CLAUDE.md

Guía técnica compacta. El detalle de cada módulo está en sus docstrings; aquí va lo que **no** se deduce leyendo un archivo suelto.

## Qué es
Simulador **pedagógico** de un horno eléctrico con control PID (Métodos Numéricos, UdeA; autor Omar Alberto Torres). **Este repositorio es solo WEB (Streamlit)**: la versión de escritorio (rich, Qt, `main.exe`) vive en `Hornovirtual_2026` y aquí no se mantiene. Código, comentarios y textos en **español**. El README es la guía para el estudiante. Plan y estado: `documentos/traspaso_version_streamlit.md` y `documentos/prompt_migracion_streamlit.txt` (las tres fases hechas; falta publicar).

**Créditos obligatorios** (`simulador_horno/creditos.py`): autor Omar Alberto Torres, docente **Yony Ceballos**, Métodos Numéricos, Ingeniería de Sistemas, UdeA, 2026 (requisito de grado). Se ven en la portada (`web/bienvenida.py`, al iniciar; botón `b_abrir`), en la barra lateral, en la ventana `ℹ Créditos` (`st.dialog`) y en el README. Nunca los quites. La portada es un componente `st.components.v2` porque `st.html` filtra el CSS animado y el SVG; la ventana existe porque volver a la portada borraría el estado de los widgets de la barra lateral.

## Comandos (desde `simulador/`)
```bash
.venv\Scripts\python -m pytest                    # 239 pruebas, ~30 s (-s muestra métricas)
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
├── modelo/         horno (derivada, Euler), perturbaciones (Impulso, EventoAleatorio, Perturbador), triac (curva, inversión, Triac)
├── control/        pid (calcular_pid puro + clase PID), anti_windup, escalado (u∈[0,1]), senal_error
├── numerico/       integradores (METODOS/NOMBRES/ORDEN/EVALUACIONES), comparacion (vs. exacta), estabilidad (R(z))
├── simulacion/     simulador (Simulador: una corrida, sin E/S), reloj, historial, metricas, resultados (CSV)
├── web/            datos (diezmado, CSV), graficas (figura del monitor en UN lienzo), indicadores (textos),
│                   monitor (componente st.components.v2), ejecucion (modo en vivo), app (página);
│                   streamlit_app.py en la raíz solo llama a app.main()
└── estilos/tema.py paleta de las gráficas (G_*); .streamlit/config.toml repite fondo, panel y texto (probado)
```
Un paso: `Simulador.paso` → `construir_error` → `PID.paso` → **registrar** → `Perturbador.entorno` → `METODOS[metodo](T, u, horno, entorno)`.

## Estado: sin globales
- Cada `Simulador(config, semilla)` tiene su `Configuracion`, `PID`, `Perturbador` (`random.Random(semilla)`) e `Historial`. Dos simuladores no comparten nada (`test_independencia`, también en hilos). **No vuelvas a meter estado a nivel de módulo.**
- La configuración se lee en **cada paso** (cambiar T_SET o KP afecta a la corrida en curso); `metodo` y `duracion` se fijan en `reiniciar()`. Modifica los campos en sitio, no reemplaces `config.pid` etc. (el PID guarda la referencia; `reiniciar` la reengancha).
- `reiniciar()` repite la corrida con la misma semilla; `semilla=None` = corrida distinta cada vez.
- El núcleo no importa ninguna interfaz (`test_capas`: ni `simulador_horno.web`, streamlit, plotly, pandas, rich ni Qt). Solo `web/` las usa.

## Decisiones y trampas (no las rompas sin querer)
- **No regresión** (`tests/test_no_regresion.py`, `tests/referencias/*.json`): huellas SHA-256 de `(t, T, error, u)` de 9 escenarios generadas ANTES de encapsular; deben coincidir **bit a bit**, también con perturbaciones, en Windows (donde se generaron). En Linux (CI) las de semilla difieren en el último bit (`sin`/`gauss` de otra libm, ~1e-15): ahí la prueba exige contadores exactos y estadísticas de las series (`series` en los JSON) con tolerancia relativa 1e-9; las corridas sin azar siguen bit a bit en todo sistema. Para ello, conserva el **orden en que se consume el generador**: medición (gauss del termopar → uniform oscilante → uniform + random del impulso) y luego la puerta. Regenerar solo si el cambio de resultados es intencional (`REGENERAR_REFERENCIAS=1`).
- **Una sola ecuación:** `modelo.horno.derivada(T, u, horno, entorno)` la usan los tres métodos. Con `ENTORNO_IDEAL` es bit a bit la fórmula original.
- **Triac (`modelo/triac.py`, `ParametrosActuador`):** el integrador recibe la FRACCIÓN que entrega el triac, no la u del PID (`Simulador.paso`: PID → entorno → `triac.aplicar` → registrar → integrar). Modo `ideal` (defecto) devuelve la misma u: corridas de referencia intactas. Curva `1 − α/180 + sen(2α)/(2π)`; inversión por bisección (38 it.) o Newton protegido (1–11 it., cae a bisección donde la derivada `−2sen²α/180` es casi 0; comprueba convergencia ANTES del respaldo, si no se queda bisecando). Límites 10°–170° (`THETA_*`): el triac no da 100 % (máx. 99,89 %). La dispersión del disparo usa `perturbador.rng` DESPUÉS de la puerta. `potencia_w = fracción × P_nominal × (V/Vn)²`; energía acumulada en J.
- **Manual/automático y límite (`ParametrosPID.modo_control`, `potencia_manual`, `limite_potencia`):** en manual `PID.seguir` ajusta la integral para que P+I+D = u (transferencia sin salto al volver). El límite satura u en `limite_potencia` y el anti-windup condicional compara con ese tope (`limitar(..., u_tope)`). Con límite 1 y automático todo es bit a bit igual.
- **Física:** `B` es propiedad derivada de `ParametrosHorno` (`(T_MAX_EQ − T_AMB)/TAU`). `u ∈ [0, 1]`. `T_INICIAL` = arranque (= `T_AMB`, en frío). ~700 mil pasos/s (B se recalcula en cada evaluación; no lo caches sin invalidarlo).
- **Velocidad ≠ física:** nunca cambia `DT`. N = factor/(HZ·DT) con fracción acumulada (`reloj.pasos_por_refresco`). La duración se respeta con `avanzar_sin_pasarse` / `completar`; `avanzar(n)` no mira la duración.
- **Registrar antes de integrar:** cada muestra `(t, T, error, u)` es del mismo instante.
- `comparacion.integrar` y `estabilidad.estudiar` trabajan sobre una **copia** del horno (`dataclasses.replace`), nunca lo modifican.
- **PID:** derivada sobre la **medición** (`−Δmedida/DT`, 0 en el primer paso). Anti-windup por defecto **condicional**; durante la subida saturada la integral queda en 0. **Recorte** reproduce el original y con KI bajo deja error permanente (probado).
- **Perturbaciones** (`limites.PERTURBACIONES`: atributo, nombre, tipo): medición (`error_oscilante`, `flag_error`, `ruido_termopar`, se suman al error) y horno (`puerta`, `red_variable`, `ambiente_variable`, vía `entorno`). Eventos por tasa/hora simulada (`p = 1 − e^(−tasa·DT/3600)`). El simulador solo **cuenta** impulsos y aperturas (`impulsos`, `aperturas`, `impulso_activo`, `puerta_abierta`); avisar es cosa de la interfaz.
- **Métricas** sobre la temperatura **real**; IAE/ISE solo comparables con igual duración.
- **CSV web** (`web.datos.csv`, decisión del usuario): estándar, `,` y punto decimal, UTF-8, en memoria; columnas `t_s,T,T_set,error,u,P,I,D,perturbacion,T_medida`. `P, I, D` normalizados (`P+I+D` = u sin saturar); `perturbacion = error − (T_set − T)`. El `Historial` guarda `setpoints` (el setpoint puede cambiar en vivo) y los tres términos.
- **CSV de disco** (`simulacion.resultados`, herencia del escritorio): `;` y coma decimal; la web no lo usa (solo lo prueba `test_resultados`/`test_dashboard`).
- **Web:** un `Simulador` + `EjecucionEnVivo` por sesión en `st.session_state`. Los widgets (claves `w_*`) se copian a `sim.config` en cada ejecución (`_aplicar_widgets`, también al inicio de cada callback de botón). En vivo: `st.fragment(run_every=1/REFRESCO_HZ)` solo mientras `en_vivo`; al terminar la corrida hace `st.rerun()` para parar el temporizador. `EjecucionEnVivo` calcula los pasos con el tiempo REAL entre refrescos (tope 1 s; la pausa no se recupera). Usa `width="stretch"`, no `use_container_width` (en desuso). La app arranca en modo En vivo a x60.
- **Monitor sin parpadeo (`web/monitor.py`):** NO uses `st.plotly_chart` para el monitor (se reconstruye en cada refresco y Streamlit lo atenúa: el usuario lo vio titilar). Es un componente `st.components.v2` (`isolate_styles=False`) montado una vez con clave fija; cada refresco envía la figura en JSON y el navegador hace `Plotly.react` en el mismo div. Plotly.js se carga del CDN jsdelivr con la versión de `plotly.offline.get_plotlyjs_version()` (requiere internet). Indicadores y avisos van dentro del componente (`web/indicadores.py`, puros). `ESTILOS_GLOBALES` anula la atenuación `[data-stale]`. El componente se registra una vez POR RUNTIME (AppTest crea uno por sesión; si no, "Component is not registered"). Verificado en Edge con Playwright (el nodo del lienzo persiste y la opacidad no baja); Playwright no está en las dependencias.
- **Lienzo (`web/graficas.figura_monitor`):** ejes con dominios manuales (curvas, horno, franja); temperatura centrada en el setpoint ACTUAL y error en 0 con el mismo `semirango` (desviación de los últimos `G_VENTANA_ESCALA_MIN` min en vivo; toda la corrida en corrida completa), mínimo ±5 °C. El dibujo del horno es un heatmap con aspecto fijo (`scaleanchor`).
- **Pestañas:** `📈 Monitor` (lienzo) y `🔢 Indicadores` (tablero agrupado + desempeño y CSV), con `st.tabs` normal (cambiar de pestaña no reejecuta Python: la corrida sigue). Cada pestaña tiene su fragmento `run_every`; solo el del monitor avanza la corrida. En vivo, el monitor muestra una **ventana deslizante** de `limites.MUESTRAS_MONITOR` (5000) muestras que corre de derecha a izquierda (`muestras_visibles`); el historial completo sigue para métricas y CSV. `datos.indices_ventana` diezma por número de muestra absoluto para que la curva no tiemble al deslizarse.

## Cómo añadir
- **Parámetro editable:** campo en la dataclass de `configuracion/parametros.py`; si va al CSV, `Simulador.parametros_corrida`.
- **Método numérico:** función `(T, u, horno, entorno=ENTORNO_IDEAL) -> T_nuevo` en `integradores.py` + `METODOS`, `NOMBRES`, `ORDEN`, `EVALUACIONES` + `_COEFICIENTES` en `estabilidad.py`.
- **Perturbación aleatoria:** usa `Perturbador.rng` (nunca el módulo `random`) y añádela al final del orden de consumo para no romper las referencias.
- **Control en la barra lateral:** widget con clave `w_<campo>` en `web/app._barra_lateral` + línea en `_aplicar_widgets`; prueba con `AppTest` en `tests/test_app.py`.
- **Dependencia:** fija la versión en `requirements.txt` (lo instala Streamlit Community Cloud).

## Pruebas (`tests/`, `pytest.ini` con `pythonpath = .`)
No necesitan pantalla ni escriben fuera de `tmp_path`. Cubren: no regresión · independencia · física · perturbaciones (semilla, tasa independiente de DT) · perturbaciones del horno · control (sobrepaso 0,54 %, t90 58 min, establecimiento 71 min) · velocidad · duración · historial · integradores y comparación (orden 1/2/4) · estabilidad (2τ y 2,785τ) · anti-windup · derivada · métricas · resultados y lectura de corridas · arranque · capas · web (diezmado, CSV, figura, modo en vivo con reloj falso, tema) · app (AppTest: carga, corrida completa, CSV, widgets, superposición, semilla, en vivo, dos sesiones, manual, límite, triac) · triac (curva, derivada, ida y vuelta, Newton vs bisección, disparo real, integración) · manual (lazo abierto, perturbación sin corregir, transferencia sin salto, límite).

## Deuda técnica conocida
1. El trapecio del primer paso usa `error_prev = 0` (efecto despreciable).
2. El modo "ciclos enteros" del actuador no está implementado (pendiente).
3. Con la física actual el sobrepaso máximo es ~2 %; uno "de libro" requiere margen de potencia y retardo del termopar (pendiente, ver traspaso §6).
4. `simulacion.resultados` (CSV en disco, `sys.frozen`) es herencia del escritorio y la web no lo usa; podría retirarse.
5. Ideas para la web (no hechas): vistas de comparación de métodos y estabilidad (`numerico.comparacion`/`estabilidad` ya dan los datos), dashboard de varias corridas de la sesión, sintonía asistida.
