# Guía de datos del firmware

Qué significa cada valor que entrega la Pico y cómo se calcula (firmware v0.2.0).

## Unidades

Casi todo está en **cuentas del ADC** (12 bits, 0 a 4095 para 0 a 3.3 V).
Una cuenta ≈ 0.806 mV. Conversión: `V = cuentas × 3.3 / 4096`.

## Qué hace la Pico en una repetición (~2.1 s)

| Tiempo | LED | Acción |
|---|---|---|
| 0–0.02 s | Apagado | Espera a que la señal se asiente |
| 0.02–1.02 s | Apagado | 1000 lecturas, una por ms → `mu_dark`, `sigma_dark` |
| 1.02–1.04 s | Encendido | Espera |
| 1.04–2.04 s | Encendido | 1000 lecturas → `mu_light`, `sigma_light` |
| ~2.1 s | Apagado | Calcula ΔV e imprime la fila |

Código: `Acquisition.measure_repetition()` en `firmware/adq.py`.

`MEASURE`: 180 s de calentamiento (~85 repeticiones completas que **no** se guardan;
sirven para que el LED llegue a su temperatura de trabajo) + 10 repeticiones que sí
se guardan + fila `SUMMARY`. Total ≈ 3 min 20 s.

## Las 19 columnas

Ejemplo real: `710386,R003,llenado_02,1,1000,1000,24.226,3.223,1853.008,19.770,1828.782,20.031,0.633,91.299,0,0,OK,0.2.0,0`

| Columna | Ejemplo | Significado | Cálculo |
|---|---|---|---|
| `timestamp_ms` | 710386 | ms desde que arrancó la Pico (no es la hora del reloj) | `time.ticks_ms()` |
| `run_id` | R003 | Identificador del MEASURE; se reinicia con la Pico | contador |
| `muestra_id` | llenado_02 | Etiqueta puesta con `SET ID=` | — |
| `rep` | 1 | Repetición 1..M, o `SUMMARY` | — |
| `N` | 1000 | Muestras por bloque | — |
| `Fs_Hz` | 1000 | Muestras por segundo | — |
| `mu_dark` | 24.2 | Promedio con LED apagado: fondo (offset del OPT101 + luz que se cuele) | media (Welford) |
| `sigma_dark` | 3.2 | Variación de **una lectura** con LED apagado | desviación estándar, n − 1 |
| `mu_light` | 1853.0 | Promedio con LED encendido: luz que atravesó + fondo | media |
| `sigma_light` | 19.8 | Variación de una lectura con LED (~1 % de la señal) | desviación estándar |
| `dV` | 1828.8 | **Señal útil** | `mu_light − mu_dark` |
| `sigma_dV` | 20.0 | Ruido de una lectura de ΔV | `√(σ_light² + σ_dark²)` |
| `sem_dV` | 0.63 | **Incertidumbre del promedio** de ΔV | `√(sem_light² + sem_dark²)`, con `sem = σ/√N` |
| `SNR` | 91.3 | Relación señal/ruido | `|dV| / sigma_dV` |
| `n_sat_light` | 0 | Lecturas ≥ 3050 con LED | conteo |
| `n_sat_dark` | 0 | Lecturas ≥ 3050 sin LED | conteo |
| `quality` | OK | `OK`, `SATURADO` (> 1 % saturadas), `RUIDO_ALTO` (σ_light/μ_light > 5 %), `ERROR:...` | `stats.quality_flag` |
| `fw_version` | 0.2.0 | Versión del firmware | `config.FW_VERSION` |
| `is_baseline` | 0 | 1 si fue `BASELINE`, 0 si fue `MEASURE` | — |

## La fila SUMMARY

Mismas columnas, otro significado. Las columnas de bloque quedan vacías.

| Columna | En una repetición | En SUMMARY |
|---|---|---|
| `dV` | ΔV de la repetición | Promedio de los M ΔV |
| `sigma_dV` | Ruido de una lectura (~20) | Variación de ΔV **entre repeticiones** (~0.7) |
| `sem_dV` | Incertidumbre de la repetición (~0.6) | `sigma_dV / √M` |
| `SNR` | ~90 | Miles: divide por la variación entre repeticiones. No comparable |
| `quality` | De la repetición | El peor de las M (ERROR > SATURADO > RUIDO_ALTO > OK) |

## Mensajes

| Mensaje | Significado |
|---|---|
| `# INICIO R003 ID=... M=10 baseline=0` | Empieza una medición |
| `# CALENTANDO 61/180 s dV=1825.9` | Avance del calentamiento (cada 30 s) |
| `# CALENTAMIENTO TERMINADO` | Desde aquí se guardan datos |
| `# FIN R003 dV=... sem=... calidad=OK` | Resumen de la medición |
| `#MON,t_s,mu_dark,mu_light,dV,sigma_light` | Líneas de `MONITOR` (en vivo, sin guardar) |
| `#ERROR ...` | Falla o comando inválido; el firmware sigue vivo |

## Ideas clave

1. **Promediar 1000 lecturas** reduce el ruido del promedio en √1000 ≈ 31 veces.
2. **`sigma` ≠ `sem`:** `sigma` es cuánto varía una lectura; `sem` es qué tan bien
   se conoce el promedio.
3. **Restar el fondo** cancela lo que afecta por igual a los dos bloques
   (luz ambiente, offsets, cambios lentos).
4. **El calentamiento** no es esperar quieto: el LED trabaja igual que al medir
   para estabilizarse (τ ≈ 69 s).
5. **Cada llenado es un solo dato** para la estadística: el ΔV de su SUMMARY.
   Las 10 repeticiones de un llenado no son independientes; usarlas como datos
   separados exageraría la significancia. La prueba de Welch se hace con un ΔV por llenado.
6. `RUIDO_ALTO` deja de tener sentido cuando la señal es muy baja (por ejemplo, si el
   PE bloquea casi toda la luz): ahí el 5 % de casi nada es casi nada.
