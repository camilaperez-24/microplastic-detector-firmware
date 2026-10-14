# Estado del proyecto — resultados, decisiones y pendientes

Actualizado: 14-oct-2026. Agregar una entrada nueva cada vez que haya una prueba o decisión importante.

## Cronología

| Fecha | Qué se hizo | Resultado clave | Evidencia |
|---|---|---|---|
| 09-oct | Repositorio, `config.py`, `stats.py` (21 tests), `record.py` (23 tests) | Núcleo estadístico validado en PC | commits iniciales |
| 10-oct | MicroPython en la Pico; prueba del ADC con GND y 3V3; `adq.py` | ADC sano; Fs real 1000.0 Hz, 0 muestras atrasadas | capturas |
| 10-oct | Paso del circuito de 5 V con divisor a 3.3 V directo; LED con 2N2222 | OPT101 saturaba con 56 Ω; se aumentó R_LED | — |
| 11-oct | Prueba de estabilidad (5 min) | Deriva exponencial, τ ≈ 69 s → calentamiento de 180 s | `evidencias/estabilidad_2026-10-11.md` |
| 11-oct | Firmware v0.2.0 completo (`io_serial`, `main`), 83 tests | Validado en la Pico | commit `88f7d5b` |
| 11-oct | Reproducibilidad sin rellenar (3 MEASURE) | ΔV 1818.0 / 1817.5 / 1816.3 → 0.05 % | `evidencias/reproducibilidad_2026-10-11.txt` |
| 12-oct | 5 llenados con agua estéril, sacando el chip | Variación entre llenados ~4 %; un atípico de −40 % | `evidencias/llenados_2026-10-12.txt` |
| 13-oct | Piloto con PE, primer intento (`pe_01`, R001) | **Inválido**: el LED no funcionaba (ΔV = 8) | `evidencias/piloto_pe_2026-10-13.txt` |

## Caracterización del instrumento

| Magnitud | Valor |
|---|---|
| Ruido del ADC (entrada a GND) | σ ≈ 2.1 cuentas (1.7 mV) |
| Fondo con LED apagado (`mu_dark`) | ≈ 24 cuentas (≈ 19 mV) en la cámara cerrada |
| Ruido por lectura con LED (`sigma_light`) | ≈ 1.05 % de la señal → viene del LED/alimentación, no del ADC |
| Transmitancia del microcanal (multímetro) | vacío 88.8 %; con agua 95.0 % |
| ΔV típico con agua limpia | 1700–1850 cuentas (≈ 1.4–1.5 V) según el llenado |
| Saturación del OPT101 a 3.3 V | ≈ 2.52 V ≈ 3128 cuentas |

## Las tres escalas de variación (hallazgo central)

| Escala | Tamaño | Causa |
|---|---|---|
| Dentro de un bloque de 1000 muestras | ~20 cuentas | Ruido de cada lectura |
| Entre repeticiones del mismo llenado | ~0.7 cuentas (0.05 %) | Estabilidad del instrumento |
| **Entre llenados distintos** | **~70 cuentas (~4 %)**, con atípicos de hasta −40 % | **Procedimiento de llenado**: posición, burbujas, gotas, cómo queda el agua en la L |

Consecuencia: el límite del sistema no es la electrónica sino el llenado.
Una burbuja puede producir una caída parecida a la de una partícula.

Datos de los 5 llenados del 12-oct (ΔV de la fila SUMMARY): 1689.5 / 1829.0 / 1801.8 / 1841.5 / 1098.7.
Con unos 10 llenados por grupo y σ ≈ 70 cuentas, la diferencia mínima detectable es de ~5 %.

## Decisiones tomadas

1. Alimentación unificada a 3.3 V desde la Pico, sin divisor en la salida del OPT101.
2. LED controlado por transistor (un GPIO no puede dar la corriente del LED).
3. Calentamiento de 180 s dentro de `MEASURE`.
4. Umbral de saturación del sensor: 3050 cuentas (provisional, falta confirmarlo con la Pico).
5. Columna `sem_dV` agregada (v0.2.0) para distinguir el ruido por lectura de la incertidumbre de la media.
6. Agua de referencia: "Agua estéril para inyección" Corpaul (Laboratorios Medifarma), 500 mL.
7. Tope en el tubo, ángulo fijo, chip marcado, regla de descarte definida antes de medir.
8. La unidad de análisis estadístico es **el llenado** (un ΔV de SUMMARY por llenado).

## Muestra de PE del piloto

- 3 partículas: 1 × 2 mm, 3 × 1 mm y 1 × 2 mm. PENDIENTE: origen, color y transparencia.
- Se cargan con pipeta plástica de 3 mm. El PE flota (densidad ~0.92–0.96 g/cm³).
- En el piloto se ubicaron a mano frente al sensor (mejor caso).

## Pendientes

1. Repetir el piloto con PE (6 llenados alternados) con el LED reparado y el tubo tapado contra la luz ambiente.
2. Documentar R_LED y la causa exacta de la falla del LED del 13-oct.
3. Confirmar el umbral de saturación midiendo con la Pico el sensor saturado.
4. Según el piloto: campaña formal (~10 llenados por grupo) o modificar la cámara para llenar sin sacar el chip (diseño pareado).
5. Código: ver la sección 7 de `CLAUDE.md`.
