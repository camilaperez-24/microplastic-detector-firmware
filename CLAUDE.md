# Contexto del proyecto para asistentes de IA

Este archivo es leído automáticamente por Claude Code y otros asistentes.
Contiene las decisiones técnicas que no deben re-cuestionarse en cada sesión.

---

## 1. Proyecto

Firmware para prototipo optoelectrónico de detección preliminar de partículas
compatibles con microplásticos tipo polietileno en agua.
Universidad Santo Tomás, Proyecto de Grado II, 2026-2.

**Alcance del firmware:**
- Adquirir señal del fotodetector.
- Controlar LED de iluminación.
- Calcular estadística por medición.
- Entregar datos por USB serial y opcionalmente por WiFi.

**Explícitamente fuera de alcance:**
- Identificación química del polímero.
- Cuantificación absoluta de concentración.
- Aprendizaje automático.
- Validación normativa o industrial.

## 2. Hardware

- **MCU:** Raspberry Pi Pico 2 W (RP2350, silicon stepping A4).
- **Sensor:** OPT101 (fotodiodo + TIA integrados, R_f interna de 1 MΩ).
- **Emisor:** LED infrarrojo + resistencia de 56 Ω en serie, controlado por GPIO.
- **Alimentación:** USB (5 V) → regulador interno de la Pico → 3V3(OUT).
  OPT101 y LED se alimentan de 3V3(OUT), NO de 5 V externo.
- **Conexión ADC:** salida del OPT101 va DIRECTA al pin ADC — SIN divisor resistivo.
  (El swing del OPT101 a 3.3 V queda naturalmente dentro del rango del ADC.)

## 3. Lenguaje y entorno

- **MicroPython 1.27+** para Pico 2 W (build RPI_PICO2_W).
- **Testing en PC:** CPython 3.11 o 3.12 + pytest.
- No usar bibliotecas que no estén en MicroPython estándar (NO numpy, NO scipy).

## 4. Decisiones técnicas no negociables

**4.1 — Estadística:**
Usar siempre el algoritmo de **Welford** en línea para media y varianza.
Nunca usar la fórmula ingenua Σx² − (Σx)²/n, que pierde precisión en float32.

**4.2 — Modulación dark/light:**
Cada medición alterna LED OFF (V_dark) y LED ON (V_light).
El observable físico útil es ΔV = V_light − V_dark.
Esto elimina deriva DC, luz ambiente y offset térmico del TIA.

**4.3 — Separación de capas:**
- `adq.py` NO imprime, NO procesa estadística. Solo llena buffers.
- `stats.py` NO toca hardware. Solo recibe listas/arrays y devuelve dicts.
- `record.py` NO ejecuta lógica de medición. Solo formatea.
- `main.py` orquesta.

Esto permite testear `stats.py` y `record.py` en PC sin la Pico.

**4.4 — Tipos de datos:**
- Lecturas crudas del ADC: `array.array('H', ...)` (uint16).
- No usar listas de Python para los bloques de muestras (memoria y velocidad).
- Pasar a float solo al calcular estadísticos.

**4.5 — Temporización:**
- No usar `time.sleep()` dentro del loop de adquisición.
- Usar `time.ticks_us()` + `time.ticks_diff()` para control de Fs.

**4.6 — Robustez:**
- Capa WiFi debe fallar silenciosamente (try/except OSError).
- Si WiFi se cae, serial y adquisición siguen funcionando.
- Toda excepción se captura y se emite como fila CSV con `quality=ERROR:<motivo>`.

## 5. Arquitectura


## 6. Contrato de datos — fila CSV

**Encabezado exacto** (una sola línea, sin espacios):

timestamp_ms,run_id,muestra_id,rep,N,Fs_Hz,mu_dark,sigma_dark,mu_light,sigma_light,dV,sigma_dV,SNR,n_sat_light,n_sat_dark,quality,fw_version,is_baseline


Cada comando `MEASURE` produce **M + 1 filas**: M repeticiones + 1 fila resumen
con `rep=SUMMARY` donde `mu_light`, `dV`, etc. son promedios sobre las M
repeticiones y `sigma_*` es la desviación entre repeticiones.

**Estados de `quality`:**
- `OK` — todas las repeticiones válidas.
- `SATURADO` — alguna rep con >1 % muestras en ADC = 4095 (12 bits).
- `RUIDO_ALTO` — σ_light / μ_light > umbral (default 5 %).
- `ERROR:<motivo>` — excepción capturada.

## 7. Comandos serial

Terminados en `\n`. Respuesta también en una línea.

- `HELLO` → devuelve versión + config + encabezado CSV.
- `SET N=1000 FS=1000 M=10 ID=agua_pura_01` → actualiza parámetros.
- `BASELINE` → medición marcada como línea base (`is_baseline=1`).
- `MEASURE` → medición estándar.
- `STREAM ON|OFF` → envío bloque-a-bloque crudo (debug).
- `WIFI ON|OFF`, `WIFI SSID=... PASS=...`.

## 8. Reglas para generación de código

- Antes de escribir código, leer `firmware/config.py` y respetar los nombres de constantes.
- Toda función pública lleva docstring con: qué recibe, qué devuelve, unidades físicas.
- Comentarios en español (es un proyecto académico colombiano).
- Nombres de variables en inglés (convención de código).
- Priorizar legibilidad sobre micro-optimización.
- Los tests en `tests/` se corren con `python -m pytest` en PC, NO en la Pico.

## 9. Orden de desarrollo

Construir de adentro hacia afuera. No pasar al siguiente paso si el anterior
no tiene su test en verde.

1. `config.py` — constantes.
2. `stats.py` + tests PC — Welford, ΔV, flags.
3. `record.py` + tests PC — formateo CSV, run_id.
4. Hola mundo en Pico (sin circuito).
5. `adq.py` básico — leer ADC, test con GND y 3V3.
6. Integración: adq + stats + serial.
7. Control LED + secuencia dark/light.
8. Parser de comandos `io_serial.py`.
9. WiFi opcional `io_wifi.py`.
10. Protocolos de validación experimental.

