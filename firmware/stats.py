"""
stats.py — Estadística del firmware
====================================

Núcleo matemático del firmware. Recibe bloques de muestras
(listas o arrays) y devuelve estadísticos.

Reglas importantes:
- Este módulo NO toca hardware (ni ADC, ni GPIO, ni serial).
- Este módulo NO imprime nada.
- Es ejecutable tanto en MicroPython (Pico) como en CPython (PC).
- Toda su lógica es testeable con pytest en PC.

Algoritmos clave:
- Welford en línea para media y varianza (numéricamente estable
  en float32, apto para MicroPython).
- Propagación de incertidumbre por suma en cuadratura para ΔV.
- Error estándar de la media: SEM = sigma / sqrt(n).

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import math

from firmware import config


# ============================================================
# 1. WELFORD — MEDIA Y DESVIACIÓN ESTÁNDAR POR BLOQUE
# ============================================================

def welford_block(samples):
    """Calcula media, desviación estándar, error estándar y saturaciones de un bloque.

    Usa el algoritmo de Welford en línea, numéricamente estable
    incluso en float de 32 bits (MicroPython en RP2350).

    Parámetros
    ----------
    samples : iterable de int o float
        Muestras crudas del ADC (típicamente uint16 de array.array).

    Devuelve
    --------
    dict con las claves:
        n       : int   — número de muestras procesadas.
        mu      : float — media muestral.
        sigma   : float — desviación estándar muestral (dividido por n-1).
                          Es el ruido de UNA muestra individual.
        sem     : float — error estándar de la media = sigma / sqrt(n).
                          Es la incertidumbre de la MEDIA.
        n_sat   : int   — número de muestras saturadas
                          (muestra >= config.SATURATION_THRESHOLD).
        min_val : int   — valor mínimo observado.
        max_val : int   — valor máximo observado.

    Si n == 0, devuelve todos los campos en 0 / 0.0.
    Si n == 1, sigma y sem se devuelven como 0.0 por convención.
    """
    n = 0
    mean = 0.0
    m2 = 0.0  # suma acumulada de cuadrados de diferencias (Welford)
    n_sat = 0
    min_val = None
    max_val = None

    sat_level = config.SATURATION_THRESHOLD

    for x in samples:
        n += 1

        # Welford: actualización en línea
        delta = x - mean
        mean = mean + delta / n
        delta2 = x - mean
        m2 = m2 + delta * delta2

        # Conteo de saturaciones (del sensor o del ADC, el menor)
        if x >= sat_level:
            n_sat += 1

        # Mínimo y máximo
        if min_val is None or x < min_val:
            min_val = x
        if max_val is None or x > max_val:
            max_val = x

    if n == 0:
        return {
            "n": 0,
            "mu": 0.0,
            "sigma": 0.0,
            "sem": 0.0,
            "n_sat": 0,
            "min_val": 0,
            "max_val": 0,
        }

    if n == 1:
        sigma = 0.0
        sem = 0.0
    else:
        variance = m2 / (n - 1)  # varianza muestral (n-1, no n)
        sigma = math.sqrt(variance)
        sem = sigma / math.sqrt(n)

    return {
        "n": n,
        "mu": mean,
        "sigma": sigma,
        "sem": sem,
        "n_sat": n_sat,
        "min_val": min_val,
        "max_val": max_val,
    }


# ============================================================
# 2. DELTA V — DIFERENCIA LIGHT - DARK
# ============================================================

def delta_v(mu_light, sigma_light, mu_dark, sigma_dark):
    """Calcula ΔV = V_light − V_dark y propaga la dispersión por muestra.

    Propagación (variables independientes, suma en cuadratura):
        σ_ΔV = sqrt(σ_light² + σ_dark²)

    Parámetros
    ----------
    mu_light, sigma_light : float — media y desviación del bloque LED ON.
    mu_dark, sigma_dark   : float — media y desviación del bloque LED OFF.

    Devuelve
    --------
    dict con las claves:
        dV       : float — mu_light − mu_dark.
        sigma_dV : float — dispersión propagada por muestra.
    """
    dv = mu_light - mu_dark
    sigma_dv = math.sqrt(sigma_light * sigma_light + sigma_dark * sigma_dark)
    return {
        "dV": dv,
        "sigma_dV": sigma_dv,
    }


def delta_v_from_blocks(block_light, block_dark):
    """Calcula ΔV, su dispersión y su error estándar a partir de dos bloques.

    Es la función que usa main.py en cada repetición.

        dV       = mu_light − mu_dark
        sigma_dV = sqrt(sigma_light² + sigma_dark²)   (ruido por muestra)
        sem_dV   = sqrt(sem_light² + sem_dark²)       (incertidumbre de la media)

    Parámetros
    ----------
    block_light : dict — salida de welford_block() para el bloque LED ON.
    block_dark  : dict — salida de welford_block() para el bloque LED OFF.

    Devuelve
    --------
    dict con las claves dV, sigma_dV y sem_dV (todas float, en cuentas).
    """
    result = delta_v(block_light["mu"], block_light["sigma"],
                     block_dark["mu"], block_dark["sigma"])
    sem_l = block_light["sem"]
    sem_d = block_dark["sem"]
    result["sem_dV"] = math.sqrt(sem_l * sem_l + sem_d * sem_d)
    return result


# ============================================================
# 3. SNR — RELACIÓN SEÑAL / RUIDO
# ============================================================

def snr(mu, sigma):
    """Calcula la relación señal/ruido simple SNR = |mu| / sigma.

    Devuelve float('inf') si sigma == 0.
    """
    if sigma == 0:
        return float("inf")
    return abs(mu) / sigma


# ============================================================
# 4. QUALITY FLAG — ESTADO DE CALIDAD
# ============================================================

def quality_flag(block_light, block_dark):
    """Determina el flag de calidad de una repetición.

    Reglas (en orden de prioridad):
    1. SATURADO: si cualquiera de los dos bloques tiene más del
       SATURATION_RATIO_LIMIT de muestras saturadas.
    2. RUIDO_ALTO: si el coeficiente de variación del bloque LIGHT
       (sigma / mu) supera NOISE_RATIO_LIMIT.
    3. OK: cualquier otro caso.

    Devuelve
    --------
    str — config.QUALITY_OK, QUALITY_SATURATED o QUALITY_HIGH_NOISE.
    """
    sat_ratio_light = block_light["n_sat"] / block_light["n"] if block_light["n"] > 0 else 0
    sat_ratio_dark = block_dark["n_sat"] / block_dark["n"] if block_dark["n"] > 0 else 0

    if sat_ratio_light > config.SATURATION_RATIO_LIMIT:
        return config.QUALITY_SATURATED
    if sat_ratio_dark > config.SATURATION_RATIO_LIMIT:
        return config.QUALITY_SATURATED

    if block_light["mu"] > 0:
        cv = block_light["sigma"] / block_light["mu"]
        if cv > config.NOISE_RATIO_LIMIT:
            return config.QUALITY_HIGH_NOISE

    return config.QUALITY_OK


def combine_quality(flags):
    """Resume los flags de varias repeticiones en un solo flag global.

    Se usa para la fila SUMMARY: la medición completa toma el peor
    estado de sus repeticiones.

    Prioridad: ERROR > SATURADO > RUIDO_ALTO > OK.

    Parámetros
    ----------
    flags : iterable de str — flags de calidad de cada repetición.

    Devuelve
    --------
    str — flag global. Si la lista está vacía, devuelve
          "ERROR:sin_repeticiones".
    """
    flags = list(flags)
    if len(flags) == 0:
        return config.QUALITY_ERROR_PREFIX + ":sin_repeticiones"
    for f in flags:
        if f.startswith(config.QUALITY_ERROR_PREFIX):
            return f
    if config.QUALITY_SATURATED in flags:
        return config.QUALITY_SATURATED
    if config.QUALITY_HIGH_NOISE in flags:
        return config.QUALITY_HIGH_NOISE
    return config.QUALITY_OK


# ============================================================
# 5. SUMMARIZE REPETITIONS — RESUMEN DE M REPETICIONES
# ============================================================

def summarize_repetitions(dv_values):
    """Resume M valores de ΔV (uno por repetición) en estadísticos agregados.

    Parámetros
    ----------
    dv_values : iterable de float — valores de ΔV de las M repeticiones.

    Devuelve
    --------
    dict con las claves:
        n_reps   : int   — número de repeticiones.
        mean_dV  : float — media de los ΔV.
        sigma_dV : float — desviación estándar ENTRE repeticiones
                           (reproducibilidad de la medición).
        sem_dV   : float — error estándar de la media de los ΔV
                           = sigma_dV / sqrt(n_reps).
        min_dV   : float — mínimo observado.
        max_dV   : float — máximo observado.
    """
    stats = welford_block(dv_values)
    return {
        "n_reps": stats["n"],
        "mean_dV": stats["mu"],
        "sigma_dV": stats["sigma"],
        "sem_dV": stats["sem"],
        "min_dV": stats["min_val"] if stats["n"] > 0 else 0.0,
        "max_dV": stats["max_val"] if stats["n"] > 0 else 0.0,
    }