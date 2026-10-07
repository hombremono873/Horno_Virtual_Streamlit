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
  El horno se representa como un **sistema de primer orden**, aplicando la **Ley de Fourier** (conducción) y la **Ley de Enfriamiento de Newton** (pérdidas al ambiente).  
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
├── requirements.txt
├── README.md
├── dist/  build/               # artefactos de compilación (main.exe)
└── simulador_horno/            # paquete de la aplicación, organizado por capas
    ├── app.py                  # bienvenida + bucle del menú (despacho por tabla)
    │
    ├── config/                 # CONSTANTES Y CONFIGURACIÓN
    │   ├── parametros_horno.py      #   valores del horno (editables desde el menú)
    │   ├── parametros_pid.py        #   ganancias y estado del PID
    │   ├── parametros_electricos.py #   ángulo de conducción
    │   ├── limites.py               #   constantes fijas del simulador
    │   └── tema.py                  #   paleta y medidas (consola + gráficas)
    │
    ├── control/                # LÓGICA DE CONTROL (sin entrada/salida)
    │   ├── modelo_termico/          #   la planta: horno.py (Euler) + integradores.py (Heun, RK4)
    │   ├── controlador/             #   pid.py + escalado.py + anti_windup.py
    │   ├── actuador/                #   angulo_conduccion.py
    │   └── perturbaciones/          #   perturbador.py + senal_error.py
    │
    ├── simulacion/             # ORQUESTACIÓN
    │   ├── simulador.py             #   clase Simulador (bucle de la corrida)
    │   └── historial.py             #   series temporales de la corrida
    │
    └── interfaces/             # INTERFACES VISUALES
        ├── consola/                 #   marco (común) + bienvenida, menu, formularios, tabla_vivo (rich)
        ├── graficas/                #   panel.py — monitor en tiempo real (pyqtgraph + PySide6)
        └── alarmas/                 #   sonora.py (beep de impulso)
```

---
# Controles

**Menú (consola)**

| Tecla | Acción |
|-------|--------|
| `↑` `↓` | Moverse entre opciones |
| `Enter` | Elegir la opción resaltada |
| `1`–`7` | Acceso directo a una opción |
| `Q` / `Esc` | Salir |

En los formularios, `Enter` sin escribir nada conserva el valor actual (se muestra entre paréntesis).

**Simulación (opción 6)**

- Se abre el **monitor**: temperatura, error y franja térmica en una sola ventana.
- Para detener: cerrar la ventana del monitor **o** pulsar `Ctrl+C` en la consola.

---
## En caso de consulta contactar a:

**Omar Alberto Torres**
**Tel:** [+57 304 344 0112](tel:+573043440112)

**Correo:** [omara.torres@udea.edu.co](mailto:omara.torres@udea.edu.co)

>**Nota:** Si necesitan información adicional sobre la ejecución o detalles técnicos del proyecto, escribemen al correo institucional.
> Tambien pueden revisar los comentarios en el código fuente para aclaraciones rápidas.
---


