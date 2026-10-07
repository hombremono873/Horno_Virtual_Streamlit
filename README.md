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
  La temperatura se actualiza en cada paso de tiempo mediante el **método de Euler**, lo que permite aproximar la evolución dinámica del sistema.

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
    │   └── integradores.py          #   Heun (RK2) y Runge-Kutta 4
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
| `1`–`8` | Acceso directo a una opción |
| `Q` / `Esc` | Salir |

En los formularios, `Enter` sin escribir nada conserva el valor actual (se muestra entre paréntesis).

**Opciones del menú**

| Opción | Qué hace |
|--------|----------|
| `1` Configurar PID | Ganancias Kp, Ki, Kd |
| `2` Configurar horno | T ambiente, setpoint, T máx. de equilibrio, τ, Δt |
| `3` Error oscilante | Ruido + senoide sobre el error |
| `4` Error de impulso | Impulsos térmicos aleatorios (~6 por hora simulada) |
| `5` Acotar integral | Límite del término integral [0-1] |
| `6` Velocidad de simulación | x1, x10, x60 (por defecto), x600 o máxima |
| `7` Ejecutar simulación | Abre el monitor en tiempo real |
| `8` Salir | Cierra el simulador |

**Velocidad de simulación (opción 6)**

El horno real tarda más de una hora en llegar a 1000 °C. La velocidad comprime
el tiempo de **ejecución**, no la física: con x60 cada segundo real equivale a un
minuto simulado y la subida completa se ve en poco más de un minuto. El paso de
integración `Δt` y los resultados son los mismos a cualquier velocidad.

**Simulación (opción 7)**

- Se abre el **monitor**: temperatura, error y franja térmica en una sola ventana,
  con el tiempo en minutos simulados.
- La consola muestra el tiempo simulado (hh:mm:ss), la velocidad activa y el tiempo real.
- Para detener: cerrar la ventana del monitor **o** pulsar `Ctrl+C` en la consola.

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


