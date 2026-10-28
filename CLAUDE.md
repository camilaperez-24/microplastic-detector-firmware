# Contexto del proyecto para Claude Code

Claude Code lee este archivo automáticamente al iniciar cada sesión.
Contiene decisiones ya tomadas y validadas con pruebas en el hardware real:
no cambiarlas sin datos nuevos que lo justifiquen.

Documentación que se carga junto con este archivo:

- @docs/estado_del_proyecto.md — resultados de las pruebas, decisiones y pendientes.
- @docs/protocolo_medicion.md — cómo se mide en el laboratorio.
- @docs/guia_de_datos.md — significado de cada columna y mensaje del firmware.

---

## 1. Proyecto

Firmware y análisis para un prototipo optoelectrónico de **detección preliminar
de partículas compatibles con microplásticos tipo polietileno (PE) en agua**.
Proyecto de Grado II, Ingeniería Electrónica, Universidad Santo Tomás, 2026-2.

- Estudiantes: Camila Pérez Mercado y Diego Alejandro Rodríguez Guzmán.
- Director: M.Sc. Oscar Mauricio Gelvez Lizarazo. Codirector: M.Sc. Carlos Javier Mojica Casallas.

**Fuera de alcance:** identificación química del polímero, cuantificación
exacta de concentración, diferenciación entre polímeros, certificación.

## 2. Cómo trabajar con este equipo

- Son estudiantes de 8.º semestre aprendiendo Git y Python. **Explicar en
  español, paso a paso, el porqué de cada cambio.**
- **Antes de modificar código, mostrar el plan y esperar aprobación.**
- Un cambio a la vez; no tocar archivos que no hacen falta para la tarea.
- Entorno: Windows 11, terminal `cmd`, entorno virtual en `venv\`
  (activar con `venv\Scripts\activate.bat`), Python 3.14, pytest 9.1.1.
  VS Code para editar y Thonny para la Pico.

## 3. Hardware (estado real, validado)

- **MCU:** Raspberry Pi Pico 2 W (RP2350), MicroPython **v1.29.0** (2026-08-24).
- **OPT101** alimentado a 3.3 V desde la Pico:
  pin 1 (V+) → 3V3 (pin 36); pines 3 y 8 → GND (pin 38);
  pin 4 unido a pin 5; **pin 5 (salida) → GP26 / pin 31, directo, sin divisor**;
  condensador de 100 nF entre pin 1 y GND.
- **LED IR** controlado por GP15 (pin 20) con transistor 2N2222:
  ánodo → 3V3; cátodo → R_LED → colector; emisor → GND; base ← 1 kΩ ← GP15.
  GP15 en alto = LED encendido. **R_LED = 470 Ω** (se aumentó desde 56 Ω porque
  el OPT101 saturaba): I_LED ≈ 4.3 mA calculada (V_F ≈ 1.2 V, V_CE(sat) ≈ 0.1 V);
  I_B ≈ 2.6 mA, el transistor trabaja saturado.
- El OPT101 a 3.3 V **satura en ~2.52 V (~3128 cuentas)**, antes que el ADC
  (4095). Por eso el umbral de saturación del firmware es 3050 cuentas.
- **Cámara:** tubo impreso en 3D, abierto por los dos extremos. El chip
  (microcanal en L) entra deslizando por una ranura; el tubo se usa inclinado
  con ángulo fijo y un tope en el extremo inferior. LED y OPT101 en paredes opuestas.
- **Fallas ya vistas:** cables que se sueltan (señal del OPT101 el 12-oct,
  LED el 13-oct), luz ambiente que entra por los extremos del tubo y sensor
  desalineado al reubicarlo (17-oct; se realineó con `MONITOR`).
- **Montaje congelado desde el 18-oct** (referencia ΔV ≈ 2221 con agua limpia):
  no mover sensor, LED ni tubo hasta terminar la campaña, salvo daño.

## 4. Firmware v0.2.0 — arquitectura

| Archivo | Capa | Dónde corre | Tests |
|---|---|---|---|
| `firmware/config.py` | Constantes (sin lógica ni hardware) | PC y Pico | indirectos |
| `firmware/adq.py` | 1 · Adquisición: LED + ADC con Fs exacta | Solo Pico | No |
| `firmware/stats.py` | 2 · Welford, sem, ΔV, calidad | PC y Pico | `tests/test_stats.py` |
| `firmware/record.py` | 3 · Filas CSV y run_id | PC y Pico | `tests/test_record.py` |
| `firmware/io_serial.py` | 4 · Parser de comandos + E/S USB no bloqueante | Parser: PC y Pico. `SerialIO`: solo Pico | `tests/test_io_serial.py` |
| `firmware/main.py` | Orquestación: calentamiento, MEASURE, MONITOR, STOP | Solo Pico | No (probado en hardware) |
| `firmware/io_wifi.py` | WiFi opcional | — | Vacío por ahora |

- **83 tests en verde** con `python -m pytest -v`.
- **Ejecución en la Pico:** la carpeta `firmware/` se sube a la raíz de la Pico
  con Thonny ("Subir a /"). Se arranca desde Thonny con un archivo local
  (fuera del repo) que contiene:
  `from firmware.main import main` y `main()`.
- **Comandos:** `HELLO`, `HELP`, `STATUS`,
  `SET ID=x N=n FS=n M=n WARMUP=s` (sin espacios alrededor de `=`),
  `MEASURE`, `BASELINE`, `MONITOR [s]`, `STOP`.
- `MEASURE` = calentamiento (180 s, sin guardar) + M = 10 repeticiones (una fila
  CSV cada una) + fila `SUMMARY`. Cada repetición: 1000 muestras con LED apagado
  y 1000 con LED encendido, a 1000 Hz.
- **Salida:** filas CSV de 19 columnas; mensajes que empiezan con `#`
  (`#ERROR`, `#MON`) para que el análisis los ignore (`comment="#"`).

## 5. Reglas no negociables

1. Media y varianza **siempre con Welford** (nunca Σx² − (Σx)²/n): la Pico usa float de 32 bits.
2. La señal útil es **ΔV = μ_light − μ_dark** (modulación dark/light del LED).
3. **Separación de capas:** `adq.py` no calcula ni imprime; `stats.py` y
   `record.py` no tocan hardware ni imprimen; `main.py` orquesta.
4. Muestras crudas en `array.array('H')`, en cuentas de 12 bits (`read_u16() >> 4`).
5. En el bucle de adquisición **no usar `sleep`**: temporizar con
   `time.ticks_us()` / `ticks_diff()` / `ticks_add()`.
6. `config.py` solo contiene constantes; nada de `import machine`.
7. El firmware no usa librerías que no existan en MicroPython (nada de numpy o scipy).
   Seguir el estilo existente: `.format()` para cadenas.
8. Toda lógica nueva que se pueda probar en PC lleva tests, y **pytest debe
   quedar en verde antes de cada commit**.
9. Si cambia el formato del CSV, **subir `FW_VERSION`**.
10. El firmware no debe caerse: los errores se informan con `#ERROR` y el LED queda apagado.
11. Comentarios y docstrings en español; nombres de variables y funciones en inglés.

## 6. Git

- Repositorio: `github.com/camilaperez-24/microplastic-detector-firmware`, rama `main`.
- Commits pequeños, mensaje estilo `tipo(alcance): descripcion` en español sin tildes
  (`feat`, `fix`, `docs`, `test`, `chore`, `refactor`).
- Las evidencias experimentales van en `evidencias/`. Los datos crudos grandes
  en `data/` no se versionan (ver `.gitignore`).

## 7. Próximos trabajos de código (orden sugerido)

1. **Script de captura en PC** (`tools/captura.py`, con pyserial): guarda en un
   `.csv` todo lo que manda la Pico y permite escribir comandos. Thonny debe estar
   cerrado mientras se usa, porque ocupa el puerto.
2. **Script de análisis** (`tools/analisis.py`, puede usar pandas/scipy/matplotlib):
   toma solo las filas `SUMMARY` válidas, agrupa por tipo de muestra
   (`limpia_*` contra `pe_*`) y aplica la **prueba t de Welch con un ΔV por
   llenado** (nunca usar las repeticiones como datos independientes). Gráficas para la tesis.
3. **Firmware v0.3:** alerta de "posible sensor desconectado" (μ_dark muy alto o
   σ muy alto) también en `MONITOR`; revisar el criterio `RUIDO_ALTO`, que no
   tiene sentido cuando el PE bloquea casi toda la luz.
4. Actualizar `README.md` con el estado real.
5. Opcional: `io_wifi.py`, arranque automático en la Pico.
