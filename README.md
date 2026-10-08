# Simulador de Horno Eléctrico con Control PID

**Universidad de Antioquia – Facultad de Ingeniería**  
**Autor:** Omar Alberto Torres  
**Docente:** Yony Ceballos  
**Fecha:** 2025  

---

##  Contexto del Proyecto

Este trabajo presenta la implementación de un **simulador computacional de un horno con regulación PID**. El objetivo es integrar conceptos de **transferencia de calor, modelado matemático y control de procesos**, mediante la aplicación de los conceptos relacionados con los conceptos de **métodos numéricos** aprendidos durante el semestre en la asignatura de métodos numéricos.  

El proyecto permite analizar de forma numérica y visual el comportamiento dinámico del sistema, además de explorar la robustez del controlador PID frente a perturbaciones externas.  

---

##  Estructura del Proyecto

El proyecto está compuesto por los siguientes elementos:

- **Código fuente en Python** desarrollado en *Visual Studio Code*.   
- **Archivo `requirements.txt`**: lista todas las librerías necesarias para crear un entorno virtual y ejecutar correctamente el simulador. 
- **Ejecutable `main.exe`**: versión compilada del proyecto que permite al usuario ejecutar la aplicación directamente, sin necesidad de crear un entorno virtual, librerías y dependencias.  

---

##  Dependencias del Proyecto

El entorno de ejecución requiere las siguientes librerías principales (incluidas en `requirements.txt`):  

- `rich` — interfaz de consola  
- `readchar` — navegación por teclado directo  
- `pyqtgraph` + `PySide6` — monitor gráfico en tiempo real  
- `numpy` — cálculo de la franja térmica  

> Requiere un entorno de escritorio (Qt). No funciona en sesiones sin interfaz gráfica.

Para instalar las dependencias en un entorno virtual:

```bash
pip install -r requirements.txt
```

Para empaquetar el ejecutable se necesita además `requirements-dev.txt` (PyInstaller).

## Ejecución del Proyecto

### Opción 1: Ejecutar desde código fuente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py                  # ejecutar desde la carpeta simulador/
```

### Opción 2: Ejecutable

Ejecutar directamente `dist\main.exe` (no requiere entorno ni dependencias).

Para regenerarlo tras cambios en el código:

```bash
pip install -r requirements-dev.txt
pyinstaller main.spec --noconfirm --clean
```

---

# Explicación compacta del código

- **Modelo térmico**  
  El horno se representa como un **sistema de primer orden**, aplicando la **Ley de Fourier** (conducción) y la **Ley de Enfriamiento de Newton** (pérdidas al ambiente):  
  `dT/dt = (T_AMB − T)/τ + B·u`, con `u ∈ [0, 1]` (un horno no enfría activamente).  
  La ganancia `B = (T_MAX_EQ − T_AMB)/τ` se deriva de la temperatura de equilibrio a potencia plena (1300 °C por defecto), lo que da un calentamiento máximo realista de ~0,42 °C/s.  
  La temperatura se actualiza en cada paso de tiempo con el método numérico elegido en el menú: **Euler** (por defecto), **Heun (RK2)** o **Runge-Kutta 4**, lo que permite comparar su precisión sobre el mismo modelo.

- **Algoritmo PID**  
  El controlador PID ajusta la energía suministrada al horno según:  
  - **Proporcional (Kp):** responde al error instantáneo.  
  - **Integral (Ki):** corrige el error acumulado en el tiempo.  
  - **Derivativa (Kd):** anticipa cambios bruscos y estabiliza la respuesta.  

  La combinación de estas tres acciones permite que la temperatura alcance el setpoint con **mínimo error en estado estacionario**, controlando el **sobreimpulso** y la **estabilidad** incluso bajo perturbaciones externas.
---
# Estructura de archivos del proyecto

```text
simulador/
├── main.py                     # punto de entrada (llama a simulador_horno.app.ejecutar)
├── main.spec                   # configuración de PyInstaller
├── requirements.txt            # dependencias de ejecución
├── requirements-dev.txt        # PyInstaller (empaquetado)
├── CLAUDE.md                   # guía técnica del código
├── pytest.ini  tests/          # pruebas automáticas (python -m pytest)
├── README.md
├── dist/  build/               # artefactos de compilación (main.exe)
└── simulador_horno/            # paquete de la aplicación
    ├── app.py                  # bienvenida + bucle del menú (despacho por tabla)
    │
    ├── configuracion/          # ¿CON QUÉ PARÁMETROS?
    │   ├── parametros_horno.py      #   valores del horno (editables desde el menú)
    │   ├── parametros_pid.py        #   ganancias y estado del PID
    │   ├── parametros_electricos.py #   ángulo de conducción
    │   ├── parametros_simulacion.py #   velocidad elegida (x1 … máxima)
    │   └── limites.py               #   constantes fijas (velocidades, muestreo, impulsos…)
    │
    ├── modelo/                 # ¿QUÉ SE SIMULA?
    │   ├── horno.py                 #   ecuación térmica + paso de Euler
    │   ├── perturbaciones.py        #   ruido, senoide e impulsos
    │   └── actuador.py              #   ángulo de conducción
    │
    ├── control/                # ¿QUIÉN CONTROLA?
    │   ├── pid.py                   #   controlador PID
    │   ├── anti_windup.py           #   recorte del término integral
    │   ├── escalado.py              #   saturación de la señal de control
    │   └── senal_error.py           #   error = setpoint − T (+ perturbaciones)
    │
    ├── numerico/               # ¿CON QUÉ MÉTODO NUMÉRICO?
    │   ├── integradores.py          #   Euler, Heun (RK2) y Runge-Kutta 4 (elegibles en el menú)
    │   ├── comparacion.py           #   comparación con la solución exacta y orden de convergencia
    │   └── estabilidad.py           #   factor de amplificación y límites de estabilidad
    │
    ├── simulacion/             # ¿QUIÉN COORDINA?
    │   ├── motor.py                 #   clase Motor: lógica de cada paso, sin E/S
    │   ├── reloj.py                 #   pasos por refresco según la velocidad
    │   ├── historial.py             #   una muestra por segundo simulado
    │   └── simulador.py             #   clase Simulador: bucle visual (motor + pantalla)
    │
    ├── interfaz/               # ¿QUÉ VE EL USUARIO?
    │   ├── consola/                 #   marco, bienvenida, menú, formularios, tabla en vivo (rich)
    │   ├── graficas/                #   panel.py — monitor en tiempo real (pyqtgraph + PySide6)
    │   └── alarmas/                 #   sonora.py (beep de impulso)
    │
    └── estilos/                # ¿CÓMO SE VE?
        └── tema.py                  #   paleta y medidas (consola + gráficas)
```

---
# Controles

**Menú (consola)**

| Tecla | Acción |
|-------|--------|
| `↑` `↓` | Moverse entre opciones |
| `Enter` | Elegir la opción resaltada |
| `1`–`9` | Acceso directo a una opción |
| `Q` / `Esc` | Salir |

En los formularios, `Enter` sin escribir nada conserva el valor actual (se muestra entre paréntesis).

**Opciones del menú**

| Opción | Qué hace |
|--------|----------|
| `1` Configurar PID | Ganancias Kp, Ki, Kd |
| `2` Configurar horno | T ambiente, setpoint, T máx. de equilibrio, τ, Δt |
| `3` Error oscilante | Ruido + senoide sobre el error |
| `4` Error de impulso | Impulsos térmicos aleatorios (~6 por hora simulada) |
| `5` Anti-windup | Ninguno, recorte de la integral o integración condicional (por defecto) |
| `6` Velocidad y duración | x1, x10, x60 (por defecto), x600 o máxima; duración de 30 min a 8 h (2 h por defecto) o sin límite |
| `7` Método numérico | Euler (por defecto), Heun (RK2) o Runge-Kutta 4 |
| `8` Ejecutar simulación | Abre el monitor en tiempo real |
| `9` Salir | Cierra el simulador |

**Velocidad y duración (opción 6)**

El horno real tarda más de una hora en llegar a 1000 °C. La velocidad comprime
el tiempo de **ejecución**, no la física: con x60 cada segundo real equivale a un
minuto simulado y la subida completa se ve en poco más de un minuto. El paso de
integración `Δt` y los resultados son los mismos a cualquier velocidad.

Después de la velocidad se elige la **duración**: 30 min, 1 h, **2 h (por defecto)**,
4 h, 8 h o sin límite, en horas simuladas. Al completarla la corrida se detiene
sola y el monitor queda abierto, con el aviso "CORRIDA TERMINADA", para analizar
las gráficas; se vuelve al menú cerrando el monitor o con `Ctrl+C`. El eje de
tiempo abarca la duración completa desde el inicio. Con la configuración por
defecto el horno llega al setpoint hacia el minuto 74, así que 2 h muestran la
subida, la llegada y la estabilización (a x60, unos 2 minutos reales).

**Método numérico (opción 7)**

Elige con qué método se resuelve en cada paso la ecuación del horno,
`dT/dt = (T_AMB − T)/τ + B·u`:

| Método | Orden | Evaluaciones por paso |
|--------|-------|-----------------------|
| Euler | 1 | 1 |
| Heun (RK2) | 2 | 2 |
| Runge-Kutta 4 | 4 | 4 |

Un método de orden p reduce su error unas 2^p veces al dividir Δt a la mitad.
Con el Δt por defecto (0,1 s) las curvas son casi idénticas; para ver la
diferencia, aumenta Δt en la opción 2 (por ejemplo a 30 s) y compara.

Dentro de esta opción, **"Comparar con la solución exacta"** integra la ecuación
a potencia plena con los tres métodos y Δt = 240, 120, 60, 30 y 15 s, y la
compara con la solución analítica `T(t) = T_eq + (T0 − T_eq)·e^(−t/τ)`:

- en la consola, una tabla con el error máximo de cada método, el **orden de
  convergencia observado** (≈ 1, 2 y 4) y el costo en evaluaciones de dT/dt;
- en una ventana, las curvas frente a la exacta, el error en el tiempo y la
  gráfica log-log de convergencia, donde la pendiente de cada recta es el orden.

**"Estabilidad con Δt grande"** muestra que un método puede fallar aunque la física
sea estable. Con la potencia apagada el horno se enfría desde el setpoint; cada
método multiplica la desviación (T − T_AMB) por un factor R en cada paso:

| Δt | Euler | Heun (RK2) | Runge-Kutta 4 |
|----|-------|------------|---------------|
| 0,5·τ | estable | estable | estable |
| 1,5·τ | **oscila** (R = −0,5) | estable | estable |
| 2,5·τ | **diverge** (llega a −7000 °C) | **diverge** | estable |
| 3·τ | diverge | diverge | **diverge** |

Límites teóricos: Euler y Heun son estables con Δt < 2τ; RK4, con Δt < ~2,785τ.

**Simulación (opción 8)**

- Se abre el **monitor**: temperatura, error y franja térmica en una sola ventana,
  con el tiempo en minutos simulados.
- La consola muestra el tiempo simulado (hh:mm:ss), la velocidad activa y el tiempo real.
- Para detener: cerrar la ventana del monitor **o** pulsar `Ctrl+C` en la consola.
- **Métricas de desempeño:** al terminar la corrida, la consola muestra
  sobrepaso (% y °C), tiempo de subida (10→90 %), tiempo al 90 %, tiempo de
  establecimiento (±1 %), error final e integrales del error IAE e ISE. Se
  calculan sobre la temperatura real del horno y quedan en pantalla hasta
  pulsar una tecla; si la corrida se detiene antes, se muestran como
  "corrida incompleta".

**Pruebas automáticas**

```bash
pip install -r requirements-dev.txt
python -m pytest
```

---
## En caso de consulta contactar a:

**Omar Alberto Torres**
**Tel:** [+57 304 344 0112](tel:+573043440112)

**Correo:** [omara.torres@udea.edu.co](mailto:omara.torres@udea.edu.co)

>**Nota:** Si necesitan información adicional sobre la ejecución o detalles técnicos del proyecto, escribemen al correo institucional.
> Tambien pueden revisar los comentarios en el código fuente para aclaraciones rápidas.
---


