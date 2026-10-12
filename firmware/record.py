"""
record.py — Construcción de filas CSV
======================================

Toma los diccionarios producidos por stats.py y los convierte
en cadenas de texto formateadas como filas CSV, respetando el
orden exacto de las columnas definido en config.CSV_COLUMNS.

Reglas importantes:
- Este módulo NO toca hardware.
- Este módulo NO imprime nada (solo devuelve strings).
- Es ejecutable tanto en MicroPython como en CPython.

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

from firmware import config


# ============================================================
# 1. GENERADOR DE RUN_ID
# ============================================================

class RunIdGenerator:
    """Genera identificadores únicos de medición.

    Cada llamada a .next() devuelve 'R001', 'R002', ... en secuencia.
    Útil para agrupar en el CSV todas las filas que pertenecen a
    la misma medición MEASURE.

    Si la Pico se reinicia, el contador vuelve a 1, pero como las
    filas también llevan timestamp_ms, no hay colisión real entre
    sesiones distintas.
    """

    def __init__(self, start=1):
        """
        Parámetros
        ----------
        start : int — valor inicial del contador (default = 1).
        """
        self._counter = start - 1

    def next(self):
        """Avanza el contador y devuelve el nuevo run_id como string.

        Formato: 'R' seguido de 3 dígitos con ceros a la izquierda
        hasta R999. A partir de R1000 crece sin padding.
        """
        self._counter += 1
        if self._counter < 1000:
            return "R{:03d}".format(self._counter)
        return "R{}".format(self._counter)

    def current(self):
        """Devuelve el último run_id generado, sin avanzar el contador.

        Si aún no se ha llamado a next(), devuelve 'R000'.
        """
        if self._counter == 0:
            return "R000"
        if self._counter < 1000:
            return "R{:03d}".format(self._counter)
        return "R{}".format(self._counter)


# ============================================================
# 2. FORMATEO DE NÚMEROS
# ============================================================

def format_number(value, decimals=3):
    """Convierte un número a string con decimales controlados.

    - Enteros se emiten sin decimales.
    - Floats se redondean al número de decimales indicado.
    - None se emite como cadena vacía.
    - Strings se devuelven tal cual (para campos como 'OK', 'R001').
    - Booleanos se emiten como '1' o '0'.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        # Nota: bool es subclase de int en Python; lo tratamos antes
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:  # NaN
            return "NaN"
        if value == float("inf"):
            return "inf"
        if value == float("-inf"):
            return "-inf"
        return "{:.{}f}".format(value, decimals)
    return str(value)


# ============================================================
# 3. CONSTRUCCIÓN DE FILA CSV
# ============================================================

def build_csv_row(data):
    """Construye una fila CSV a partir de un diccionario de campos.

    Recorre config.CSV_COLUMNS en orden y toma de 'data' el valor
    de cada columna. Si una columna no está en el diccionario,
    se emite como cadena vacía.

    Devuelve
    --------
    str — línea CSV completa, sin salto de línea al final.
    """
    campos = []
    for col in config.CSV_COLUMNS:
        valor = data.get(col, "")
        campos.append(format_number(valor))
    return ",".join(campos)


# ============================================================
# 4. ENSAMBLADO DE FILA DE REPETICIÓN
# ============================================================

def row_for_repetition(timestamp_ms, run_id, muestra_id, rep,
                        block_light, block_dark, dv_result,
                        quality, is_baseline=False):
    """Ensambla una fila CSV para una repetición individual.

    Parámetros
    ----------
    timestamp_ms : int   — ms desde arranque de la Pico.
    run_id       : str   — identificador de la medición (ej. 'R005').
    muestra_id   : str   — ID textual de la muestra (ej. 'agua_pura_01').
    rep          : int   — número de repetición (1..M).
    block_light  : dict  — salida de stats.welford_block() para LED ON.
    block_dark   : dict  — salida de stats.welford_block() para LED OFF.
    dv_result    : dict  — salida de stats.delta_v_from_blocks()
                           (claves dV, sigma_dV y sem_dV).
    quality      : str   — flag de calidad de la repetición.
    is_baseline  : bool  — True si esta medición es línea base.

    Devuelve
    --------
    str — línea CSV lista para imprimir.
    """
    sigma_dv = dv_result["sigma_dV"]
    if sigma_dv == 0:
        snr_val = float("inf")
    else:
        snr_val = abs(dv_result["dV"]) / sigma_dv

    data = {
        "timestamp_ms": timestamp_ms,
        "run_id": run_id,
        "muestra_id": muestra_id,
        "rep": rep,
        "N": block_light["n"],
        "Fs_Hz": config.FS_HZ,
        "mu_dark": block_dark["mu"],
        "sigma_dark": block_dark["sigma"],
        "mu_light": block_light["mu"],
        "sigma_light": block_light["sigma"],
        "dV": dv_result["dV"],
        "sigma_dV": dv_result["sigma_dV"],
        "sem_dV": dv_result.get("sem_dV", ""),
        "SNR": snr_val,
        "n_sat_light": block_light["n_sat"],
        "n_sat_dark": block_dark["n_sat"],
        "quality": quality,
        "fw_version": config.FW_VERSION,
        "is_baseline": is_baseline,
    }
    return build_csv_row(data)


# ============================================================
# 5. ENSAMBLADO DE FILA SUMMARY
# ============================================================

def row_for_summary(timestamp_ms, run_id, muestra_id, N, dv_summary,
                     quality, is_baseline=False):
    """Ensambla la fila SUMMARY que resume las M repeticiones.

    Parámetros
    ----------
    timestamp_ms : int   — ms al momento de emitir el resumen.
    run_id       : str   — mismo run_id de las repeticiones.
    muestra_id   : str   — mismo muestra_id de las repeticiones.
    N            : int   — número de muestras por bloque (para contexto).
    dv_summary   : dict  — salida de stats.summarize_repetitions()
                           (claves mean_dV, sigma_dV y sem_dV).
    quality      : str   — flag de calidad global (stats.combine_quality).
    is_baseline  : bool  — True si es medición de línea base.

    Devuelve
    --------
    str — línea CSV SUMMARY lista para imprimir.
    """
    sigma_dv = dv_summary["sigma_dV"]
    if sigma_dv == 0:
        snr_val = float("inf")
    else:
        snr_val = abs(dv_summary["mean_dV"]) / sigma_dv

    data = {
        "timestamp_ms": timestamp_ms,
        "run_id": run_id,
        "muestra_id": muestra_id,
        "rep": "SUMMARY",  # cadena especial que distingue esta fila
        "N": N,
        "Fs_Hz": config.FS_HZ,
        "mu_dark": "",       # no aplica al resumen
        "sigma_dark": "",
        "mu_light": "",
        "sigma_light": "",
        "dV": dv_summary["mean_dV"],
        "sigma_dV": dv_summary["sigma_dV"],
        "sem_dV": dv_summary.get("sem_dV", ""),
        "SNR": snr_val,
        "n_sat_light": "",
        "n_sat_dark": "",
        "quality": quality,
        "fw_version": config.FW_VERSION,
        "is_baseline": is_baseline,
    }
    return build_csv_row(data)