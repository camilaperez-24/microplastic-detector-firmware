"""
adq.py — Capa 1: adquisición
=============================

Controla el LED infrarrojo y lee bloques de muestras del ADC
con una frecuencia de muestreo exacta.

Reglas importantes:
- Este módulo SOLO corre en la Pico (usa el módulo 'machine').
- NO se prueba con pytest en el PC.
- NO calcula estadística (eso es stats.py).
- NO imprime nada (eso es io_serial.py).
- La lógica del LED (activo en alto o en bajo) sale de config.LED_ACTIVE_LOW:
  el resto del firmware siempre piensa en "prendido" / "apagado".

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import gc
import time
from array import array

from machine import ADC, Pin

from firmware import config


FS_MAX_HZ = 10000
"""Frecuencia de muestreo máxima permitida, en Hz.
Por encima de esto, MicroPython no alcanza a mantener tiempos
exactos entre muestras."""


def led_level(on):
    """Nivel del pin GP15 para prender (on=True) o apagar (on=False) el LED.

    Circuito original (protoboard): GP15 en alto prende el LED → nivel 1.
    Prototipo nuevo (13-nov): el LED prende con GP15 en bajo → nivel 0.
    """
    if config.LED_ACTIVE_LOW:
        return 0 if on else 1
    return 1 if on else 0


class Acquisition:
    """Adquisición de bloques de muestras y control del LED.

    Uso típico:
        acq = Acquisition()
        dark, light = acq.measure_repetition()
    """

    def __init__(self, n_samples=config.N_SAMPLES, fs_hz=config.FS_HZ):
        """Inicializa el ADC, el pin del LED y los buffers.

        Parámetros
        ----------
        n_samples : int — muestras por bloque (default config.N_SAMPLES).
        fs_hz     : int — frecuencia de muestreo en Hz (default config.FS_HZ).
        """
        self.adc = ADC(config.PIN_ADC_SIGNAL)
        # El LED arranca apagado por seguridad
        self.led = Pin(config.PIN_LED_IR, Pin.OUT, value=led_level(False))
        self.last_fs_real = 0.0
        self.last_overruns = 0
        self.configure(n_samples, fs_hz)

    def configure(self, n_samples, fs_hz):
        """Cambia N y Fs, y reserva de nuevo los buffers.

        Parámetros
        ----------
        n_samples : int — muestras por bloque, mínimo 2.
        fs_hz     : int — frecuencia de muestreo en Hz, de 1 a FS_MAX_HZ.

        Lanza ValueError si los valores están fuera de rango.
        """
        if n_samples < 2:
            raise ValueError("n_samples debe ser >= 2")
        if fs_hz < 1 or fs_hz > FS_MAX_HZ:
            raise ValueError("fs_hz debe estar entre 1 y {}".format(FS_MAX_HZ))

        self.n = n_samples
        self.fs = fs_hz
        # Periodo entre muestras en microsegundos
        self.period_us = 1000000 // fs_hz
        # Buffers reservados una sola vez (uint16)
        self.buf_dark = array("H", [0] * n_samples)
        self.buf_light = array("H", [0] * n_samples)

    def set_led(self, on, settle=True):
        """Enciende o apaga el LED infrarrojo.

        Parámetros
        ----------
        on     : bool — True enciende, False apaga.
        settle : bool — si es True, espera config.LED_SETTLE_MS
                        para que la señal del fotodetector se estabilice.
        """
        self.led.value(led_level(on))
        if settle:
            # Esta espera está FUERA del bucle de muestreo, por eso
            # aquí sí se permite usar sleep.
            time.sleep_ms(config.LED_SETTLE_MS)

    def read_block(self, buf):
        """Llena 'buf' con self.n muestras del ADC a self.fs Hz.

        Cada muestra se guarda en cuentas de 12 bits (0 a 4095).

        Parámetros
        ----------
        buf : array('H') — buffer de destino, de tamaño self.n.

        Devuelve
        --------
        array('H') — el mismo buffer, ya lleno.

        Efectos secundarios
        -------------------
        Actualiza self.last_fs_real (Hz) y self.last_overruns
        (número de muestras que salieron tarde).
        """
        # Limpiar memoria ANTES de medir, para que no interrumpa el bloque
        gc.collect()

        # Referencias locales: hacen el bucle más rápido en MicroPython
        read = self.adc.read_u16
        period = self.period_us
        n = self.n
        overruns = 0

        t_start = time.ticks_us()
        t_next = t_start

        for i in range(n):
            # Esperar hasta el instante exacto de esta muestra
            while time.ticks_diff(time.ticks_us(), t_next) < 0:
                pass
            # read_u16 entrega 16 bits; >> 4 lo lleva a 12 bits reales
            buf[i] = read() >> 4
            # Programar la siguiente muestra a partir del horario,
            # no de la hora actual (así el error no se acumula)
            t_next = time.ticks_add(t_next, period)
            # Si ya pasamos la hora de la siguiente, va a salir tarde
            if time.ticks_diff(time.ticks_us(), t_next) > 0:
                overruns += 1

        duration_us = time.ticks_diff(time.ticks_us(), t_start)
        if duration_us > 0:
            self.last_fs_real = (n - 1) * 1000000 / duration_us
        else:
            self.last_fs_real = 0.0
        self.last_overruns = overruns
        return buf

    def measure_repetition(self):
        """Ejecuta una repetición completa: bloque dark + bloque light.

        Secuencia: LED apagado → esperar → leer bloque dark →
                   LED encendido → esperar → leer bloque light →
                   LED apagado.

        Devuelve
        --------
        tuple (buf_dark, buf_light) — dos array('H') de self.n muestras.
        """
        self.set_led(False)
        self.read_block(self.buf_dark)
        self.set_led(True)
        self.read_block(self.buf_light)
        # Apagar el LED al terminar (no hace falta esperar aquí)
        self.set_led(False, settle=False)
        return self.buf_dark, self.buf_light

    def shutdown(self):
        """Deja el hardware en estado seguro: LED apagado."""
        self.led.value(led_level(False))
