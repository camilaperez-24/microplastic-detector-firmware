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

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import math

from firmware import config


# ============================================================
# 1. WELFORD — MEDIA Y DESVIACIÓN ESTÁNDAR POR BLOQUE
# ============================================================

def welford_block(samples):
    """Calcula media, desviación estándar y conteo de saturaciones de un bloque.

    Usa el algoritmo de Welford en línea, numéricamente estable
    incluso en float de 32 bits (MicroPython en RP2350).

    Parámetros
    ----------
    samples : iterable de int o float
        Muestras crudas del ADC (típicamente uint16 de array.array).
        Puede ser una lista, tuple, array.array o cualquier iterable.

    Devuelve
    --------
    dict con las claves:
        n       : int   — número de muestras procesadas.
        mu      : float — media muestral.
        sigma   : float — desviación estándar muestral (dividido por n-1).
        n_sat   : int   — número de muestras saturadas
                          (muestra >= config.ADC_SATURATION_VALUE).
        min_val : int   — valor mínimo observado.
        max_val : int   — valor máximo observado.

    Si n == 0, devuelve todos los campos en 0 / 0.0.
    Si n == 1, sigma se devuelve como 0.0 (no está definido, pero es
    útil como convención para no romper el flujo).
    """
    n = 0
    mean = 0.0
    m2 = 0.0  # suma acumulada de cuadrados de diferencias (Welford)
    n_sat = 0
    min_val = None
    max_val = None

    sat_level = config.ADC_SATURATION_VALUE

    for x in samples:
        n += 1

        # Welford: actualización en línea
        delta = x - mean
        mean = mean + delta / n
        delta2 = x - mean
        m2 = m2 + delta * delta2

        # Conteo de saturaciones
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
            "n_sat": 0,
            "min_val": 0,
            "max_val": 0,
        }

    if n == 1:
        sigma = 0.0
    else:
        variance = m2 / (n - 1)  # varianza muestral (n-1, no n)
        sigma = math.sqrt(variance)

    return {
        "n": n,
        "mu": mean,
        "sigma": sigma,
        "n_sat": n_sat,
        "min_val": min_val,
        "max_val": max_val,
    }


# ============================================================
# 2. DELTA V — DIFERENCIA LIGHT - DARK
# ============================================================

def delta_v(mu_light, sigma_light, mu_dark, sigma_dark):
    """Calcula ΔV = V_light − V_dark y propaga la incertidumbre.

    Esta es la cantidad físicamente útil del firmware: la señal
    real debida al LED, limpia de deriva DC, luz ambiente y
    offset térmico del TIA.

    Propagación de incertidumbre (variables independientes,
    suma en cuadratura):
        σ_ΔV = sqrt(σ_light² + σ_dark²)

    Parámetros
    ----------
    mu_light     : float — media del bloque con LED ON.
    sigma_light  : float — desviación estándar del bloque con LED ON.
    mu_dark      : float — media del bloque con LED OFF.
    sigma_dark   : float — desviación estándar del bloque con LED OFF.

    Devuelve
    --------
    dict con las claves:
        dV       : float — mu_light − mu_dark.
        sigma_dV : float — incertidumbre propagada.
    """
    dv = mu_light - mu_dark
    sigma_dv = math.sqrt(sigma_light * sigma_light + sigma_dark * sigma_dark)
    return {
        "dV": dv,
        "sigma_dV": sigma_dv,
    }


# ============================================================
# 3. SNR — RELACIÓN SEÑAL / RUIDO
# ============================================================

def snr(mu, sigma):
    """Calcula la relación señal/ruido simple SNR = |mu| / sigma.

    Es una métrica aproximada de calidad del bloque. Un SNR alto
    significa que la señal media es grande comparada con el ruido.

    Parámetros
    ----------
    mu    : float — media (típicamente mu_light o ΔV).
    sigma : float — desviación estándar correspondiente.

    Devuelve
    --------
    float — |mu| / sigma. Si sigma == 0, devuelve float('inf')
            (señal perfectamente estable, ruido cero).
    """
    if sigma == 0:
        return float("inf")
    return abs(mu) / sigma


# ============================================================
# 4. QUALITY FLAG — ESTADO DE CALIDAD DEL BLOQUE
# ============================================================

def quality_flag(block_light, block_dark):
    """Determina el flag de calidad de una repetición.

    Reglas (en orden de prioridad):
    1. SATURADO: si cualquiera de los dos bloques tiene más del
       SATURATION_RATIO_LIMIT de muestras saturadas.
    2. RUIDO_ALTO: si el coeficiente de variación del bloque LIGHT
       (sigma / mu) supera NOISE_RATIO_LIMIT.
    3. OK: cualquier otro caso.

    Parámetros
    ----------
    block_light : dict — salida de welford_block() para el bloque LED ON.
    block_dark  : dict — salida de welford_block() para el bloque LED OFF.

    Devuelve
    --------
    str — uno de: config.QUALITY_OK, QUALITY_SATURATED, QUALITY_HIGH_NOISE.
    """
    # 1. Chequeo de saturación en cualquiera de los dos bloques
    sat_ratio_light = block_light["n_sat"] / block_light["n"] if block_light["n"] > 0 else 0
    sat_ratio_dark = block_dark["n_sat"] / block_dark["n"] if block_dark["n"] > 0 else 0

    if sat_ratio_light > config.SATURATION_RATIO_LIMIT:
        return config.QUALITY_SATURATED
    if sat_ratio_dark > config.SATURATION_RATIO_LIMIT:
        return config.QUALITY_SATURATED

    # 2. Chequeo de ruido relativo en el bloque LIGHT
    if block_light["mu"] > 0:
        cv = block_light["sigma"] / block_light["mu"]
        if cv > config.NOISE_RATIO_LIMIT:
            return config.QUALITY_HIGH_NOISE

    # 3. Todo bien
    return config.QUALITY_OK


# ============================================================
# 5. SUMMARIZE REPETITIONS — RESUMEN DE M REPETICIONES
# ============================================================

def summarize_repetitions(dv_values):
    """Resume M valores de ΔV (uno por repetición) en estadísticos agregados.

    Devuelve la media de los ΔV de todas las repeticiones y la
    desviación estándar ENTRE repeticiones. Esto es distinto de
    la σ dentro de un bloque — mide la reproducibilidad de la
    medición completa.

    Parámetros
    ----------
    dv_values : iterable de float — valores de ΔV de las M repeticiones.

    Devuelve
    --------
    dict con las claves:
        n_reps      : int   — número de repeticiones.
        mean_dV     : float — media de los ΔV.
        sigma_dV    : float — desviación estándar entre repeticiones.
        min_dV      : float — mínimo observado.
        max_dV      : float — máximo observado.

    Internamente usa welford_block() para no duplicar lógica.
    """
    stats = welford_block(dv_values)
    return {
        "n_reps": stats["n"],
        "mean_dV": stats["mu"],
        "sigma_dV": stats["sigma"],
        "min_dV": stats["min_val"] if stats["n"] > 0 else 0.0,
        "max_dV": stats["max_val"] if stats["n"] > 0 else 0.0,
    }