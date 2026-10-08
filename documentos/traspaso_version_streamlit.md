# Traspaso: de la versión de escritorio a la versión Streamlit

Documento para retomar el trabajo en esta carpeta (`SImuladorTempStreamlit`) sin perder el contexto del proyecto de escritorio. **Léelo completo antes de empezar.** Fue escrito el 2026-10-08, al terminar la versión de escritorio.

## 1. Origen de esta copia
- Copia de `C:\Users\usuario\Desktop\SimuladorTemperatura\simulador`, la versión de **escritorio**, que sigue viva en GitHub: `hombremono873/Hornovirtual_2026`, rama `main`, commit `ff24dac`.
- La versión de escritorio está **completa y probada**: 141 pruebas y GitHub Actions en verde. No hay que hacerle nada más salvo que el usuario lo pida.
- Esta carpeta es para la **versión web con Streamlit**, que irá en un **repositorio nuevo de GitHub**, distinto del de escritorio.

## 2. ⚠️ Antes del primer commit en esta carpeta
1. **Cambiar el remoto.** Todavía apunta al repositorio de escritorio. Pídele al usuario la URL del repositorio nuevo y luego:
   `git remote set-url origin https://github.com/hombremono873/<repositorio-nuevo>.git`
   y verifica con `git remote -v`. **No hagas push hasta comprobarlo.**
2. **Rama:** la copia quedó en la rama `perturbaciones-dashboard`, con el mismo commit que `main` en GitHub (`ff24dac`). Deja `main` en ese commit (`git branch -f main ff24dac`, `git checkout main`) y borra la otra rama.
3. **Entorno virtual:** el `.venv` copiado apunta a la carpeta vieja. Recréalo con `python -m venv .venv --clear` y luego `pip install -r requirements.txt -r requirements-dev.txt`. Comprueba con `python -m pytest` que pasen las 141 pruebas.
4. **Carpetas generadas:** `build/`, `dist/` y `.pytest_cache/` vinieron en la copia y se pueden borrar; están en `.gitignore`.

## 3. El plan de trabajo
- El prompt literal del usuario está en `documentos/prompt_migracion_streamlit.txt`. Tiene tres fases y pide un commit por fase.
- **Usa rutas viejas**, anteriores a la reorganización:
  - `config/` → `configuracion/`
  - `interfaces/` → `interfaz/`
  - `config/tema.py` → `estilos/tema.py`
  - `control/controlador/escalado.py` → `control/escalado.py`
- **Su requisito previo ya se cumple:** la física realista y el factor de velocidad están hechos. Muchas cosas que pide ya existen y deben **reutilizarse, no reescribirse**:
  - **Duración, velocidad y métricas** (incluidas IAE e ISE): `simulacion/reloj.py`, `simulacion/metricas.py`.
  - **CSV:** `simulacion/resultados.py`. Hoy usa `;` y coma decimal para Excel en español; el prompt pide un CSV de descarga. Decide con el usuario el formato de la web.
  - **Lógica de un paso sin E/S:** `simulacion/motor.py`.
  - **Perturbaciones del horno, de la medición y anti-windup** elegibles: `modelo/perturbaciones.py`, `modelo/horno.py` (`derivada` + `entorno`), `control/anti_windup.py`.
  - **Comparación con la solución exacta y estabilidad:** `numerico/comparacion.py`, `numerico/estabilidad.py`.
  - **Dashboard de corridas:** `interfaz/consola/dashboard.py` y `interfaz/graficas/dashboard.py`. Sirve de referencia para la vista de comparación web.
- **La Fase 1 del prompt (encapsular el estado en clases) es también el pago de la deuda técnica:**
  - estado global en variables de módulo, que en un servidor web se compartiría entre usuarios;
  - estado del impulso en atributos de función;
  - el trapecio del primer paso.

  **El usuario decidió pagarla aquí, en la versión Streamlit, no en la de escritorio.**
- **No regresión:** antes de refactorizar, guarda corridas de referencia con semilla fija (sin y con perturbaciones) y compáralas después. Sin perturbaciones deben coincidir bit a bit. En el escritorio esto se verificó con huellas SHA-256 de las series `(T, u, error)`.

## 4. Cómo trabaja el usuario (Omar Alberto Torres, autor; UdeA, Métodos Numéricos)
- Escribe en español, en mensajes cortos. "Autorizado", "si" y "apruebo lo correcto" significan que acepta la recomendación.
- **Flujo que espera:**
  1. Plan breve.
  2. Su autorización.
  3. Rama nueva y **un commit por ítem**.
  4. Pruebas (`pytest`).
  5. Una guía de prueba paso a paso que diga qué debe ver.
  6. Su prueba.
  7. **Merge y push solo cuando confirma.**
- Uso **pedagógico**: el simulador es para estudiantes. Valora las explicaciones conceptuales (qué es IAE, por qué Euler oscila) y los experimentos que se ven en clase.
- Windows en español (Colombia).
- Mantén `README.md` (guía para estudiantes) y `CLAUDE.md` (técnico y **compacto**: el usuario pidió optimizar tokens) al día en cada cambio.

## 5. Trampas técnicas ya conocidas
- En Bash, `sed` con `\|` es alternancia: una vez reemplazó todas las palabras "error" de `CLAUDE.md`. Para editar texto usa Python (`str.replace` con un `assert` del conteo) o la herramienta Edit.
- Los heredocs con `\n` dentro de cadenas Python se corrompen al pasar por la terminal. Para textos con `\n` usa la herramienta Edit.
- Pruebas con `PYTHONIOENCODING=utf-8`. Qt sin pantalla: `QT_QPA_PLATFORM=offscreen` y, para capturas con texto, `QT_QPA_FONTDIR=C:/Windows/Fonts`.
- Explorar sintonías es barato: el motor hace ~1,3 millones de pasos por segundo.

## 6. Pendientes que siguen abiertos
1. **Opción B, pendiente de autorización:** sobrepaso "de libro" del 5–15 %. Con la física actual el máximo es ~2 %, porque el setpoint está al 75 % de la capacidad y la planta es de primer orden sin retardo. Requiere margen de potencia (`T_MAX_EQ` ≈ 2000), retardo del termopar y resintonía.
2. **Sintonía asistida:** Ziegler-Nichols o minimizar el IAE.
3. **Conectar `modelo/actuador.py`** (ángulo de conducción). Opcional.
4. **Nota en la pantalla de estabilidad** de que solo Euler oscila. Ya está en el README.
5. **AL FINAL DEL PROYECTO, importante para el usuario: escribir un ARTÍCULO sobre el horno virtual.** Antes, acordar con él la audiencia, el formato (revista, congreso o informe UdeA) y la extensión. Material:
   - el modelo y la compresión de tiempo;
   - los órdenes observados 1,01, 2,02 y 4,02;
   - los límites de estabilidad 2τ y 2,785τ (Euler con 2,5τ predice −7336 °C);
   - el anti-windup: ninguno da 29 % de sobrepaso, el recorte falla con KI bajo y el condicional es robusto;
   - las métricas, las perturbaciones, el dashboard y las pruebas.
