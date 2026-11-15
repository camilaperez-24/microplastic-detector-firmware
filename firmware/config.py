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

FW_VERSION = "0.2.1"
"""Versión del firmware. Cambiar al liberar una nueva iteración.
Se emite en cada fila CSV para trazabilidad.
0.2.0: columna sem_dV, saturación del sensor, calentamiento.
0.2.1: WiFi y página web opcionales (el CSV no cambia; la versión
       sirve para saber qué datos se tomaron con esta versión)."""


# ============================================================
# 2. PINES
# ============================================================
# Numeración de GPIO de la Raspberry Pi Pico 2 W.
# ADC0 = GPIO26, ADC1 = GPIO27, ADC2 = GPIO28.

PIN_ADC_SIGNAL = 26
"""GPIO del pin ADC que recibe la salida del OPT101.
Corresponde a ADC0 (canal 0 del ADC)."""

PIN_LED_IR = 15
"""GPIO que controla el LED infrarrojo a través del transistor 2N2222.
En alto = LED ON, en bajo = LED OFF."""

LED_ACTIVE_LOW = False
"""True si el LED prende con GP15 en bajo. La protoboard y el prototipo final
(baquelita, verificado el 14-nov) usan False. Lo lee adq.led_level()."""


# ============================================================
# 3. ADQUISICIÓN
# ============================================================

N_SAMPLES = 1000
"""Número de muestras por bloque de adquisición.
Un bloque dura N_SAMPLES / FS_HZ segundos."""

FS_HZ = 1000
"""Frecuencia de muestreo del ADC, en Hz.
Con N=1000 y Fs=1000 Hz, cada bloque dura 1 segundo.
Validado en la Pico: 1000.0 Hz reales, 0 muestras atrasadas."""


# ============================================================
# 4. MODULACIÓN DARK / LIGHT Y TIEMPOS
# ============================================================

M_REPETITIONS = 10
"""Número de repeticiones por medición completa.
Cada repetición = 1 bloque LED OFF + 1 bloque LED ON."""

LED_SETTLE_MS = 20
"""Tiempo de espera en milisegundos después de encender
o apagar el LED, antes de empezar a muestrear."""

WARMUP_S = 180
"""Tiempo de calentamiento antes de medir, en segundos.
Determinado en la prueba de estabilidad del 2026-10-11:
la señal se estabiliza con tau ~ 69 s y a los 180 s queda
a menos de 1 cuenta de su valor final.
Ver evidencias/estabilidad_2026-10-11.md"""


# ============================================================
# 5. UMBRALES DE CALIDAD
# ============================================================

ADC_SATURATION_VALUE = 4095
"""Valor máximo del ADC de 12 bits (2^12 - 1)."""

SENSOR_SATURATION_COUNTS = 3050
"""Umbral de saturación del OPT101, en cuentas.
Alimentado a 3.3 V, el OPT101 no supera ~2.52 V (~3128 cuentas),
por lo que satura ANTES que el ADC. Se deja un margen:
cualquier muestra >= 3050 cuentas (~2.46 V) se considera saturada.
PROVISIONAL: confirmar midiendo con la Pico el sensor saturado."""

SATURATION_THRESHOLD = min(ADC_SATURATION_VALUE, SENSOR_SATURATION_COUNTS)
"""Umbral efectivo de saturación que usa stats.py:
el menor entre el límite del ADC y el del sensor."""

SATURATION_RATIO_LIMIT = 0.01
"""Fracción máxima de muestras saturadas permitida por bloque.
Si se supera, la medición se marca como SATURADO. 0.01 = 1 %."""

NOISE_RATIO_LIMIT = 0.05
"""Coeficiente de variación máximo (sigma / mu) en el bloque LED ON.
Si se supera, la medición se marca como RUIDO_ALTO. 0.05 = 5 %."""


# ============================================================
# 6. ADC — CONSTANTES DE HARDWARE
# ============================================================

ADC_BITS = 12
"""Resolución del ADC del RP2350. No cambiar."""

ADC_VREF = 3.3
"""Voltaje de referencia del ADC, en voltios."""

ADC_LSB_V = ADC_VREF / (2 ** ADC_BITS)
"""Voltios por cuenta del ADC: ~0.806 mV."""


# ============================================================
# 7. SERIAL
# ============================================================

SERIAL_BAUDRATE = 115200
"""Velocidad del puerto USB serial, en baudios."""


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
    "sem_dV",
    "SNR",
    "n_sat_light",
    "n_sat_dark",
    "quality",
    "fw_version",
    "is_baseline",
]
"""Lista de columnas del CSV, en orden de emisión.
sigma_dV = dispersión de cada muestra individual.
sem_dV   = incertidumbre de la media (error estándar)."""

CSV_HEADER = ",".join(CSV_COLUMNS)
"""Cadena única con el encabezado del CSV, lista para imprimir."""


# ============================================================
# 9. ESTADOS DE CALIDAD
# ============================================================

QUALITY_OK = "OK"
QUALITY_SATURATED = "SATURADO"
QUALITY_HIGH_NOISE = "RUIDO_ALTO"
QUALITY_ERROR_PREFIX = "ERROR"  # se usa como "ERROR:motivo"


# ============================================================
# 10. WIFI Y PÁGINA WEB (OPCIONAL)
# ============================================================
# La Pico crea su propia red y sirve una página en http://192.168.4.1.
# La contraseña de la red NO va aquí: va en firmware/secrets.py, que no
# se sube a GitHub (ver .gitignore). Copiar secrets_ejemplo.py y cambiarla.
# Plan y contrato de la página: docs/plan_wifi.md.

WIFI_ENABLED = False
"""Switch global del WiFi. Con False el firmware se comporta exactamente
como en la campaña (solo USB). Se deja en False hasta hacer la prueba de
validación (docs/plan_wifi.md, sección 7)."""

WIFI_AP_SSID = "Detector-PE"
"""Nombre de la red WiFi que crea la Pico."""

WIFI_AP_PASSWORD_MIN_LEN = 8
"""Largo mínimo de la contraseña (WPA2 no acepta menos de 8 caracteres)."""

WEB_PORT = 80
"""Puerto HTTP. Con 80 basta escribir la IP en el navegador."""

WEB_PAGE_PATH = "/firmware/web/index.html"
"""Ruta de la página dentro de la Pico (se sube junto con firmware/)."""

WEB_CLIENT_TIMEOUT_S = 0.5
"""Tiempo máximo esperando a que un celular termine de enviar su petición.
Corto a propósito: mientras tanto la medición espera entre repeticiones."""

WEB_MAX_REQUESTS_PER_POLL = 3
"""Peticiones que se atienden como máximo en cada turno del servidor."""

WEB_SERIES_POINTS = 120
"""Puntos de ΔV que guarda la gráfica de la página (uno por repetición)."""

WEB_MAX_MSGS = 8
"""Mensajes del firmware que muestra la página."""

SESSION_DIR = "/datos"
"""Carpeta de la Pico donde se guarda una copia de cada sesión
(sesion_001.csv, sesion_002.csv, ...), con el formato de la Shell de Thonny."""

T_REL_THRESHOLD = 0.80
"""Umbral de clasificación de la página: T_rel = ΔV / ΔV_referencia.
Por debajo de 0.80 el llenado se marca "PE probable" (mismo umbral de la campaña)."""


# ============================================================
# 11. MUESTRA — IDENTIFICADOR POR DEFECTO
# ============================================================

DEFAULT_SAMPLE_ID = "sin_id"
"""ID de muestra por defecto cuando el operador no fija uno."""