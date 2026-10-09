"""
config.py — Constantes del firmware
====================================

Archivo central de configuración. Solo contiene constantes,
nunca lógica ni importaciones de hardware.

Todos los demás módulos del firmware importan desde aquí.
Si necesitas cambiar un pin, una frecuencia o un umbral,
este es el único archivo que debes tocar.

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

# ============================================================
# 1. METADATOS DEL FIRMWARE
# ============================================================

FW_VERSION = "0.1.0"
"""Versión del firmware. Cambiar al liberar una nueva iteración.
Se emite en cada fila CSV para trazabilidad."""


# ============================================================
# 2. PINES
# ============================================================
# Numeración de GPIO de la Raspberry Pi Pico 2 W.
# ADC0 = GPIO26, ADC1 = GPIO27, ADC2 = GPIO28.

PIN_ADC_SIGNAL = 26
"""GPIO del pin ADC que recibe la salida del OPT101.
Corresponde a ADC0 (canal 0 del ADC)."""

PIN_LED_IR = 15
"""GPIO que controla el LED infrarrojo (encendido/apagado).
En alto = LED ON, en bajo = LED OFF."""


# ============================================================
# 3. ADQUISICIÓN
# ============================================================

N_SAMPLES = 1000
"""Número de muestras por bloque de adquisición.
Un bloque dura N_SAMPLES / FS_HZ segundos."""

FS_HZ = 1000
"""Frecuencia de muestreo del ADC, en Hz.
Con N=1000 y Fs=1000 Hz, cada bloque dura 1 segundo."""


# ============================================================
# 4. MODULACIÓN DARK / LIGHT
# ============================================================

M_REPETITIONS = 10
"""Número de repeticiones por medición completa.
Cada repetición = 1 bloque LED OFF + 1 bloque LED ON.
Una medición completa toma: M * 2 * (N / Fs) segundos
(más los tiempos de estabilización del LED)."""

LED_SETTLE_MS = 20
"""Tiempo de espera en milisegundos después de encender
o apagar el LED, antes de empezar a muestrear.
Permite que la señal del fotodetector se estabilice."""


# ============================================================
# 5. UMBRALES DE CALIDAD
# ============================================================

ADC_SATURATION_VALUE = 4095
"""Valor máximo del ADC de 12 bits (2^12 - 1).
Cualquier muestra igual o superior se considera saturada."""

SATURATION_RATIO_LIMIT = 0.01
"""Fracción máxima de muestras saturadas permitida por bloque.
Si se supera, la medición se marca como SATURADO.
0.01 = 1% de las muestras."""

NOISE_RATIO_LIMIT = 0.05
"""Coeficiente de variación máximo (sigma / mu) en el bloque LED ON.
Si se supera, la medición se marca como RUIDO_ALTO.
0.05 = 5% de ruido relativo."""


# ============================================================
# 6. ADC — CONSTANTES DE HARDWARE
# ============================================================

ADC_BITS = 12
"""Resolución del ADC del RP2350. No cambiar."""

ADC_VREF = 3.3
"""Voltaje de referencia del ADC, en voltios.
En la Pico 2 W, el ADC usa VREF = 3V3 del regulador interno."""

ADC_LSB_V = ADC_VREF / (2 ** ADC_BITS)
"""Resolución del ADC en voltios por cuenta (LSB = Least Significant Bit).
Para 12 bits y 3.3 V: ~0.806 mV por cuenta."""


# ============================================================
# 7. SERIAL
# ============================================================

SERIAL_BAUDRATE = 115200
"""Velocidad del puerto USB serial, en baudios.
115200 es el estándar y es rápido para CSV línea a línea."""


# ============================================================
# 8. CONTRATO DE DATOS — COLUMNAS DEL CSV
# ============================================================
# Orden exacto en que se emiten las columnas en cada fila.
# NO cambiar sin actualizar record.py y la documentación.

CSV_COLUMNS = [
    "timestamp_ms",
    "run_id",
    "muestra_id",
    "rep",
    "N",
    "Fs_Hz",
    "mu_dark",
    "sigma_dark",
    "mu_light",
    "sigma_light",
    "dV",
    "sigma_dV",
    "SNR",
    "n_sat_light",
    "n_sat_dark",
    "quality",
    "fw_version",
    "is_baseline",
]
"""Lista de columnas del CSV, en orden de emisión.
Record.py construye cada fila respetando este orden."""

CSV_HEADER = ",".join(CSV_COLUMNS)
"""Cadena única con el encabezado del CSV, lista para imprimir."""


# ============================================================
# 9. ESTADOS DE CALIDAD
# ============================================================
# Valores permitidos para el campo 'quality' de cada fila.

QUALITY_OK = "OK"
QUALITY_SATURATED = "SATURADO"
QUALITY_HIGH_NOISE = "RUIDO_ALTO"
QUALITY_ERROR_PREFIX = "ERROR"  # se usa como "ERROR:motivo"


# ============================================================
# 10. WIFI (OPCIONAL)
# ============================================================
# Por defecto deshabilitado. Si se activa, las credenciales reales
# deben vivir en firmware/secrets.py (NO versionado — ver .gitignore).

WIFI_ENABLED = False
"""Switch global para WiFi. Si es False, io_wifi.py no intenta conectarse."""

WIFI_ENDPOINT_URL = ""
"""URL del endpoint HTTP al que se envían las filas resumen.
Vacío = no enviar."""

WIFI_TIMEOUT_S = 5
"""Timeout de las operaciones de red, en segundos.
Si se supera, la fila se descarta silenciosamente."""


# ============================================================
# 11. MUESTRA — IDENTIFICADOR POR DEFECTO
# ============================================================

DEFAULT_SAMPLE_ID = "sin_id"
