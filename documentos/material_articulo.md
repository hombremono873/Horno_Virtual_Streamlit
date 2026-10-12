# Material para el artículo del horno virtual

Recopilación de TODO lo que debe explicar el artículo final sobre el simulador. Se va completando en cada sesión: no borrar nada; si algo cambia, anotar el cambio y su fecha.

Fórmulas en texto plano (sin LaTeX), con ejemplos numéricos, como pidió el autor.

**Pendiente antes de redactar:** acordar con el autor la audiencia (estudiantes, jurado, revista), el formato (revista, congreso, informe UdeA) y la extensión.

---

## 0. Créditos (obligatorios)

- **Título:** Simulador virtual de horno con control PID.
- **Autor:** Omar Alberto Torres.
- **Docente:** Yony Ceballos.
- **Asignatura:** Métodos Numéricos.
- **Programa:** Ingeniería de Sistemas.
- **Institución:** Universidad de Antioquia, Facultad de Ingeniería.
- **Año:** 2026.
- **Contexto:** proyecto de la asignatura, requisito de grado.
- **Uso:** el horno simulado representa un **horno de joyería para fundición (casting)**. En joyería la red es de 220 o 110 VCA.

---

## 1. Qué es el horno virtual

Un simulador pedagógico de un horno eléctrico controlado por un PID. Integra transferencia de calor, modelado matemático, control de procesos y **métodos numéricos**.

**Historia de versiones:**
1. **Escritorio:** menú de consola con rich, monitor gráfico con Qt y un ejecutable `main.exe`. Repositorio Hornovirtual_2026.
2. **Web:** Streamlit y Plotly, para usarlo desde el navegador sin instalar nada. Repositorio Horno_Virtual_Streamlit, con Streamlit Community Cloud como destino.

**Para el artículo:** de la migración se aprende que el estado global (variables de módulo) impedía que varios usuarios usaran la app a la vez. Se encapsuló en objetos: cada sesión tiene su propio simulador, controlador, perturbaciones e historial. Lo verifica una prueba con dos simulaciones intercaladas y en hilos.

---

## 2. El sistema completo (lazo de control)

```
setpoint ──► error ──► PID ──► u (potencia pedida) ──► actuador (triac) ──► potencia real
   ▲                                                                          │
   │                                                                          ▼
 sensor (termopar) ◄──────────── temperatura del horno ◄──────────── ecuación del horno
```

### Las tres temperaturas (aclaración pedida por el autor)

| Nombre | Qué es | Quién la conoce |
|---|---|---|
| T (real) | La temperatura verdadera del horno, la que calcula la ecuación | Solo la física |
| medida | Lo que lee el termopar: T + ruido del sensor | El controlador |
| setpoint | La temperatura deseada (por ejemplo 1000 °C) | El controlador |

```
medida = T + ruido del sensor
error  = setpoint − medida
```

En el código se calcula primero el error y luego se despeja la medida (`medida = setpoint − error`). Las dos formas dan el mismo resultado.

**Ejemplo:** T = 950 °C y ruido de +2 °C → medida = 952 °C → error = 1000 − 952 = 48 °C. El error real es 50 °C, pero el controlador no lo sabe.

- El error alimenta P e I. La medida alimenta D.
- La temperatura real se usa para las métricas y es la curva verde de la gráfica.

---

## 3. El modelo térmico del horno

```
variación de temperatura por segundo = (T_ambiente − T) / τ  +  B × (potencia que llega)
```

- **τ (constante de tiempo, s):** la inercia térmica. Por defecto 3000 s.
- **B (ganancia térmica, °C/s):** cuánto calienta el horno a potencia plena. Se calcula, no se elige:
  ```
  B = (T_MAX_EQ − T_ambiente) / τ = (1300 − 30) / 3000 ≈ 0,4233 °C/s
  ```
  T_MAX_EQ es la temperatura a la que llegaría el horno con el 100 % de la potencia, para siempre.
- **La potencia que llega** es una fracción entre 0 y 1: la u del PID con el actuador ideal, o lo que entrega el triac.

**Historia, muy importante para el artículo:**
- **Primera versión:** B = 100 °C/s, elegido para que la corrida fuera corta. Con ese valor el equilibrio a potencia plena era de unos **300 000 °C**, algo absurdo.
- **También en la primera versión,** u iba de −1 a 1: con u negativa el horno "enfriaba" activamente, y una resistencia no puede quitar calor.
- **Corrección:** física realista. B sale de T_MAX_EQ y u va de 0 a 1. Lo que se comprime ahora es el tiempo de ejecución (la velocidad), no la física.

**Perturbaciones que entran a la ecuación:** la red variable multiplica la potencia por (V/Vn)²; la puerta abierta agrega pérdidas, con TAU_PUERTA = 1500 s, lo que triplica las pérdidas; el ambiente variable oscila ±10 °C en 1 h.

### Inercia térmica y hornos pequeños (tema pedido por el autor)

De la potencia nominal sale la capacidad térmica equivalente:
```
C = potencia nominal / B    →  3000 W / 0,4233 = 7087 J/°C
h = C / τ                   →  7087 / 3000    = 2,36 W/°C   (pérdidas al ambiente)
```
- **Un horno pequeño** (como los de joyería) tiene menor C: con la misma potencia calienta y se enfría más rápido, le afectan más las perturbaciones (abrir la puerta) y necesita otra sintonía.
- **La inercia filtra** las variaciones rápidas de potencia, como el temblor del triac (ver 7.6).
- **Experimentos sugeridos:** comparar τ = 3000 s con valores menores y con distintas potencias.

---

## 4. El controlador PID

En cada paso de tiempo (Δt = 0,1 s):

```
P = Kp × error

integral = integral anterior + (error + error anterior) / 2 × Δt      (regla del trapecio)
I = Ki × integral

derivada = −(lectura actual − lectura anterior) / Δt                  (sobre la MEDICIÓN)
D = Kd × derivada

u sin recortar = (P + I + D) / 20000
u = recortar entre 0 y 1   (o entre 0 y el límite de potencia, si hay límite)
```

Valores por defecto: Kp = 200, Ki = 10, Kd = 2.

**Ejemplo en régimen:** error 2 °C, integral 1450, derivada −0,1:
```
P = 200 × 2     =    400
I = 10 × 1450   = 14 500
D = 2 × (−0,1)  =     −0,2
u = 14 899,8 / 20 000 = 0,745   →  74,5 % de la potencia
```
En régimen casi toda la potencia la pone **I**.

**Al arrancar en frío:** error = 970 °C → P = 200 × 970 / 20 000 = 9,7, que es mayor que 1, así que u = 1 (potencia máxima).

**Derivada sobre la medición (corrección histórica):** antes se derivaba el error, y en el primer paso D = Kd × 970 / 0,1 = **19 400**: un pico enorme, el llamado "derivative kick". Ahora se deriva la medida y vale 0 en el primer paso. Con el setpoint fijo es equivalente, pero no produce picos al arrancar ni al cambiar el setpoint.

**Detalle conocido:** en el primer paso, el trapecio usa error anterior = 0. El efecto es despreciable.

### El divisor 20000 (U_MAX)

- **Origen (palabras del autor):** lo eligió por **intuición**, "para intentar escalizar y evitar que u fuera siempre cero o uno". No salió de un cálculo. Estaba en la primera versión, del 7 de octubre de 2026, con Kp = 35.
- **Lectura técnica:** dividir la suma entre 20000 equivale a dividir cada ganancia:
  ```
  Kp real = 200 / 20000 = 0,01     →  1 % de potencia por cada °C de error
  Ki real =  10 / 20000 = 0,0005
  Kd real =   2 / 20000 = 0,0001
  ```
  Solo importa el cociente ganancia / U_MAX: con U_MAX = 10000 y la mitad de las ganancias, el controlador se comporta igual.
- **Banda proporcional:** U_MAX / Kp = 20000 / 200 = **100 °C**. Con más de 100 °C de error, P solo satura u en 1; con menos, el controlador dosifica. Si se dividiera entre un número muy pequeño, u saltaría entre 0 y 1 como un termostato. Eso es lo que la intuición del autor evitó.
- **La potencia de régimen no depende de U_MAX;** la fija la física:
  ```
  u en régimen = (setpoint − ambiente) / (T_MAX_EQ − ambiente) = 970 / 1270 ≈ 0,764
  ```
  La integral se acomoda sola hasta dar ese valor.
- **Decisión pendiente del autor:** dejar U_MAX y explicarlo (recomendado), o quitarlo y usar ganancias normalizadas. Los resultados serían idénticos.

---

## 5. El anti-windup

**Windup:** mientras u está saturada en 1 (durante la subida), el error se sigue acumulando en la integral aunque la potencia ya no pueda subir más. Al llegar al setpoint, esa integral "inflada" mantiene la potencia alta y el horno se pasa.

| Modo | Regla | Resultado medido |
|---|---|---|
| Ninguno | Integra siempre | **29 % de sobrepaso (~280 °C)**; el IAE sube ~19 % |
| Recorte (el original) | Si la integral supera 2000, se multiplica por 0,85 | Funciona con las ganancias por defecto, pero **con Ki bajo deja error permanente**: el tope impide aportar la potencia que el equilibrio necesita |
| Condicional (por defecto) | No integra si u está saturada y el error empuja hacia el mismo lado | Robusto con cualquier sintonía |

**Con límite de potencia** (ver 8), el condicional compara contra ese límite en vez de contra 1. Con un límite de 60 %, la integral no se infla: es más de 10 veces menor que sin anti-windup (verificado).

---

## 6. Métodos numéricos

### 6.1 Integradores de la ecuación del horno
- **Euler:** orden 1, una evaluación por paso.
- **Heun (RK2):** orden 2, dos evaluaciones.
- **Runge-Kutta 4:** orden 4, cuatro evaluaciones.

Los tres usan una sola definición de la ecuación (`derivada`), así que las perturbaciones físicas actúan igual con cualquier método.

**Órdenes observados,** comparando con la solución exacta T(t) = T_eq + (T0 − T_eq) × e^(−t/τ) con Δt = 240, 120, 60, 30 y 15 s: **1,01; 2,02 y 4,02**.

### 6.2 Estabilidad
- Con la potencia apagada, cada método multiplica la desviación por un factor R en cada paso, con z = −Δt/τ:
  - Euler: R = 1 + z
  - Heun: R = 1 + z + z²/2
  - RK4: R = 1 + z + z²/2 + z³/6 + z⁴/24
- Hay estabilidad si |R| < 1. **Límites:** Euler y Heun hasta Δt < 2τ; RK4 hasta Δt < ~2,785τ.
- **Ejemplo:** Euler con Δt = 2,5τ predice **−7336 °C**, aunque la física es estable.
- **Solo Euler oscila:** R < 0 para Δt entre τ y 2τ. Heun y RK4, cuando fallan, divergen sin oscilar.

### 6.3 Inversión de la curva del triac (ver 7.3)
Es el puente entre el control y la asignatura: una ecuación trascendente resuelta por **bisección** y por **Newton-Raphson** en cada paso del control.

### 6.4 No regresión y reproducibilidad
- Antes de reorganizar el código se guardaron 9 corridas de referencia, con huellas SHA-256 de las series. Después del cambio dieron **bit a bit** iguales, también las corridas con perturbaciones, gracias a que se mantuvo el orden en que se consumen los números aleatorios.
- **Hallazgo:** en Linux (GitHub Actions), las 2 corridas con ruido en la medición difieren solo en el **último bit**: un error relativo máximo de 4,5 × 10⁻¹⁵. La causa es que `sin` y `gauss` vienen de otra biblioteca matemática. Las corridas sin azar son idénticas en cualquier sistema. Es una buena lección sobre la aritmética de punto flotante.
- **Semilla:** con la misma semilla y la misma configuración, la corrida se repite exactamente.

---

## 7. El actuador: el triac

### 7.1 Funcionamiento físico
El triac recorta cada medio ciclo de la red: espera un **ángulo de disparo α**, de 0° a 180°, y conduce desde ahí. Con 0° pasa toda la potencia; con 90°, la mitad; con 180°, nada. La potencia **no es proporcional** al ángulo:
```
fracción de potencia = 1 − α/180 + sen(2α) / (2 × 3,1416)
```
Valores: 0° → 1; 10° → 0,9989; 90° → 0,5; 170° → 0,0011; 180° → 0.

Pendiente de la curva: −2 × sen²(α) / 180. Vale 0 en 0° y en 180°: la curva es plana en los extremos.

Unidades: R = V² / potencia nominal (220 V y 3000 W → 16,13 Ω); voltaje eficaz = V × raíz(fracción); potencia = V²/R × fracción.

### 7.2 Los tres actuadores del simulador
| Actuador | Qué hace | Resultado |
|---|---|---|
| **Ideal** | Llega exactamente la u pedida | Referencia teórica (por defecto) |
| **Triac lineal** | α = 180 × (1 − u), la conversión ingenua | Llega otra potencia: menos de la pedida bajo el 50 % (25 % → 9,1 %), más por encima (76,4 % → **92,3 %**); coincide en 0 %, 50 % y 100 %. El PID compensa pidiendo menos y aun así llega a 1000 °C: **el lazo cerrado corrige un actuador mal calibrado** |
| **Triac compensado** | Halla α tal que fracción(α) = u, invirtiendo la curva | Llega lo pedido (25 % → 113,83°; 50 % → 90°; 76,4 % → **64,65°**) |

### 7.3 Inversión numérica (medido, tolerancia 10⁻⁹ grados)
| Potencia pedida | α | Iteraciones de Newton | Iteraciones de bisección |
|---|---|---|---|
| 0,1 % | 170,376° | 11 | 38 |
| 5 % | 143,647° | 8 | 38 |
| 50 % | 90,000° | 1 | 38 |
| 76,4 % | 64,649° | 6 | 38 |
| 99 % | 20,879° | 9 | 38 |
| 99,9 % | 9,624° | 11 | 38 |

- **Bisección:** siempre 38 iteraciones, porque 180 / 2³⁸ < 10⁻⁹. Converge siempre.
- **Newton-Raphson protegido:** α nuevo = α − (fracción(α) − u) / pendiente(α). Cerca de 0° y de 180° la pendiente es casi 0 y el paso se dispara; en ese caso usa un paso de bisección dentro del intervalo que contiene la raíz.
- **Anécdota para el artículo, sobre criterios de parada:** la primera versión de Newton, al caer **exactamente** en la raíz, calculaba un paso nulo que quedaba en el borde del intervalo. El código lo tomaba como "fuera del intervalo" y se ponía a bisecar. Con u = 0,99 usaba 44 iteraciones en vez de 9. Lo detectó una prueba automática, y se corrigió comprobando la convergencia antes del respaldo.

### 7.4 Comportamiento en los extremos (pregunta del autor, 2026-10-11)
- **Ángulo pedido menor que 10°:** apenas hay voltaje para cebar el triac; el controlador deja la compuerta activa todo el ciclo → **conducción completa (100 %)**.
- **Ángulo pedido mayor que 170°:** el medio ciclo se está acabando y la corriente no alcanza la **corriente de mantenimiento** → **no conduce (0 %)**.
- **Antes de este ajuste,** el ángulo se recortaba al límite: 99,89 % y 0,11 %.

### 7.5 Resolución y dispersión del disparo
- **Resolución:** paso mínimo del temporizador. Con 1° (unos 46 microsegundos a 60 Hz), un pedido de 64,65° se dispara en 65° → 75,7 % en vez de 76,4 %. El PID corrige alternando entre 64° y 65°, y la potencia muestra escalones.
- **Dispersión:** error aleatorio (gaussiano) del instante de disparo. Con 0,5°, el 95 % de los disparos cae dentro de ±1°. Es una perturbación del **actuador**, no del sensor; usa la semilla de la corrida. Si empuja el disparo más allá de 170°, ese medio ciclo no conduce.

### 7.6 La inercia filtra
Los escalones y el temblor de la potencia casi no mueven la temperatura, porque la inercia térmica (C, τ) los promedia.

### 7.7 Energía
Potencia en vatios = fracción × potencia nominal × (V/Vn)². La energía acumulada se muestra en kWh, con la corriente y el voltaje eficaz.

---

### 7.8 El osciloscopio (idea del autor, 2026-10-12)
Pantalla de dos ciclos de la red (a 60 Hz, 16,67 ms por ciclo) con un solo eje de tiempo:
- **CH1 voltaje de la red:** voltaje pico × sen(ángulo); voltaje pico = 220 × raíz(2) ≈ 311 V.
- **CH2 voltaje en la resistencia:** igual a la red desde el disparo α hasta el cruce por cero; 0 antes. Es la onda **recortada**.
- **Voltaje en el triac:** red − carga. Mientras el triac no conduce, todo el voltaje queda sobre él.
- **CH3 corriente:** voltaje en la carga / R. Tiene la misma forma porque la carga es resistiva y está en fase.
- **CH4 potencia instantánea:** voltaje × corriente, siempre positiva (pico ≈ 6000 W con 220 V y 16,13 Ω).
- **CH5 pulso de compuerta:** el circuito detecta el cruce por cero, espera α (a 60 Hz cada grado son 46,3 µs; 64,65° → **2,993 ms**) y envía un pulso corto (2°, ~93 µs). El triac se enciende y sigue conduciendo solo hasta el siguiente cruce por cero: el pulso es la **causa** y la onda recortada el **efecto**. Hay un pulso por medio ciclo. Por debajo de 10° la compuerta queda activa todo el ciclo; por encima de 170° no hay pulso ni conducción.

**Lectura con el mouse:** un recuadro con todos los canales en el mismo instante. Ejemplo con α = 64,65° en 186,5° eléctricos: red −35,2 V, carga 0 V, el triac bloquea los −35,2 V, corriente 0 A.

**Comprobación numérica (puente con Métodos Numéricos):** la potencia media se calcula **integrando la onda** con la regla del trapecio (promedio = (1/T) × integral de voltaje × corriente) y se compara con la fórmula cerrada del triac:
```
α = 30°     integrada 2913,494 W   fórmula 2913,497 W   diferencia relativa 9e-7
α = 64,65°  integrada 2291,979 W   fórmula 2291,981 W   diferencia relativa 1e-6
α = 113,83° integrada  749,912 W   fórmula  749,910 W   diferencia relativa 3e-6
α = 150°    integrada   86,506 W   fórmula   86,503 W   diferencia relativa 3e-5
```
Cerca de 180° conduce pocos grados y el error del trapecio (malla de 0,25°) pesa más. La onda tiene un **salto vertical** en el disparo; para integrarlo bien se agregan dos muestras, una justo antes y otra justo en el disparo.

**Anécdotas de redondeo, buenas para el artículo:**
- Al reducir el ángulo al medio ciclo, 360 + 64,65 da 64,6499999… en lugar de 64,65. En ese punto el triac "no conducía" y la potencia salía 0,7 W menor (0,03 %). Se corrigió con una tolerancia de 10⁻⁷ grados.
- En α = 180° la fórmula daba −2 × 10⁻¹⁷ en lugar de 0, y la raíz cuadrada del voltaje eficaz fallaba. Se fuerza a que la fracción nunca sea negativa.

**Diseño:** se actualiza una vez por segundo (unos 140 kB por envío) mientras el monitor va a 4 por segundo. En vivo muestra el ángulo de la simulación; con el actuador ideal, el ángulo equivalente. En modo explorar el ángulo se mueve a mano.

## 8. Control manual, automático y límite de potencia (aprobado 2026-10-11)

- **Automático:** el PID decide u.
- **Manual (lazo abierto):** el usuario fija la potencia en % o el ángulo α, que se mantienen sincronizados. El setpoint queda solo como referencia. Sin perturbaciones, el horno llega a:
  ```
  temperatura final = ambiente + potencia × (T_MAX_EQ − ambiente) = 30 + 0,764 × 1270 ≈ 1000 °C
  ```
  Pero llega más lento: su t90 es más de 1,5 veces el del PID. Y **nadie corrige** una perturbación: con la puerta abriéndose, en manual la temperatura se queda abajo y el PID la recupera.
- **Transferencia sin salto:** en manual, el PID "sigue" a la potencia manual ajustando su integral para que P + I + D = u. Al volver a automático no hay golpe de potencia; solo cambia la acción integral normal de un paso. Sin ese seguimiento, P solo saturaría u en 1.
- **Límite de potencia (automático):** el PID no puede pedir más del tope fijado. Con 60 %, el horno no pasa de **30 + 0,6 × 1270 ≈ 792 °C**: simula un horno con poca potencia instalada.

---

## 9. Perturbaciones

| Sobre la **medición** (el controlador lee mal) | Sobre el **horno** (cambia la física) |
|---|---|
| Error oscilante: senoide de 20 °C + ruido | Apertura de puerta: ~2 por hora, 90 s, pérdidas triplicadas |
| Impulsos: ±80 °C, ~6 por hora (tasa configurable) | Red: voltaje ±6 % → potencia ±12 % (P ∝ V²) |
| Ruido del termopar: gaussiano de 1 °C | Ambiente: ±10 °C en 1 h |
| | (Actuador) resolución y dispersión del triac |

Los eventos aleatorios se definen por tasa por hora simulada: p = 1 − e^(−tasa × Δt / 3600). Así no dependen de Δt.

---

## 10. Métricas de desempeño (sobre la temperatura real)

- **Sobrepaso:** cuánto se pasa del setpoint, en °C y en % del salto. Si el horno arranca por encima del setpoint, se mide por debajo.
- **Tiempos:** al 10 % y al 90 % del salto; tiempo de subida (de 10 % a 90 %); establecimiento (desde cuándo queda siempre dentro de ±1 %).
- **Error final.**
- **IAE** = integral de |error| (°C·min): el área entre la curva y el setpoint.
- **ISE** = integral de error² (°C²·min): castiga los errores grandes.
- IAE e ISE solo se comparan entre corridas de igual duración.
- **Corrida por defecto (2 h):** sobrepaso **0,54 %**, tiempo al 90 % **58,2 min**, establecimiento **70,6 min**.
- **Límite de la física actual:** el sobrepaso máximo alcanzable es ~2 %. Uno "de libro", de 5 a 15 %, requiere margen de potencia y retardo del termopar (opción B, pendiente).

---

## 11. Compresión del tiempo (velocidad)

Velocidades: x1, x10, x60, x600 y máxima. La velocidad cambia el número de pasos por refresco, nunca Δt:
```
pasos por refresco = factor / (refrescos por segundo × Δt)
```
En la web, los pasos se calculan con el tiempo **real** transcurrido entre refrescos, para que el factor se cumpla aunque el navegador vaya irregular.

---

## 12. La aplicación web (decisiones de diseño)

- **Portada animada con los créditos** al iniciar; los créditos también están en la barra lateral, en la ventana "Créditos" y en el README.
- **Monitor en un solo lienzo,** como el de escritorio: temperatura, error con u y la potencia entregada, paredes del horno coloreadas y franja térmica.
- **Eje centrado en el setpoint** (y el error en 0), con escala según la desviación reciente: amplio durante la subida, ±5 °C en régimen.
- **Sin parpadeo:** el monitor es un componente que vive en el navegador y se actualiza con Plotly.react, en lugar de reconstruirse 4 veces por segundo.
- **Ventana deslizante de 5000 muestras** (~83 min) que corre de derecha a izquierda. El diezmado es estable (por número de muestra) para que la curva no tiemble.
- **Pestañas:** Monitor, Indicadores (incluye actuador e inercia), Actuador (curva del triac en vivo y tabla Newton contra bisección) y Osciloscopio (ver 7.8). Cambiar de pestaña no detiene la corrida.
- **CSV estándar** (coma y punto decimal): t_s, T, T_set, error, u, P, I, D, perturbación, T_medida, alfa_grados, fracción_potencia, potencia_W, energía_kWh.
- **Pruebas automáticas:** unas 240, en Windows y en Linux (GitHub Actions).

---

## 13. Decisiones pendientes y trabajo futuro

1. U_MAX: dejarlo y explicarlo, o quitarlo (sección 4).
2. Valores por defecto realistas para un horno de joyería: potencia, temperatura de trabajo, T_MAX_EQ, τ (preguntar al autor).
3. Modo "ciclos enteros" del actuador (alternativa industrial casi lineal).
4. Opción B: sobrepaso "de libro", con retardo del termopar y margen de potencia.
5. Sintonía asistida: Ziegler-Nichols o minimizar el IAE.
6. Pestañas de Métodos Numéricos (comparación con la exacta y estabilidad) y Dashboard de corridas.

---

## Registro de cambios de este documento
- 2026-10-11: creación con todo lo tratado hasta la implementación del triac, el control manual, el límite de potencia y el comportamiento en los extremos del ángulo.
- 2026-10-12: sección 7.8, el osciloscopio (canales, pulso de compuerta, lectura con el mouse, potencia integrada contra la fórmula y anécdotas de redondeo).
