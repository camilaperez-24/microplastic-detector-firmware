"""
main.py — Orquestación del firmware
====================================

Junta todas las capas:
    io_serial  →  recibe comandos del operador
    adq        →  controla el LED y adquiere bloques
    stats      →  calcula media, sigma, sem, ΔV y calidad
    record     →  arma las filas CSV
    io_serial  →  envía filas y mensajes al PC

Flujo de una medición (comando MEASURE o BASELINE):
    1. Calentamiento: repite dark/light durante WARMUP segundos sin
       guardar datos, para que el LED llegue a su equilibrio térmico.
       Cada 30 s informa cómo va ΔV.
    2. M repeticiones: una fila CSV por repetición.
    3. Fila SUMMARY con el promedio y la dispersión de las M repeticiones.
    En cualquier momento se puede cancelar con STOP.

Para correrlo desde Thonny:
    from firmware.main import main
    main()

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import time

from firmware import config
from firmware import stats
from firmware import record
from firmware.adq import Acquisition
from firmware.io_serial import SerialIO, parse_command, HELP_TEXT


WARMUP_REPORT_S = 30
"""Cada cuántos segundos se informa el avance del calentamiento."""

MONITOR_HEADER = "#MON,t_s,mu_dark,mu_light,dV,sigma_light"
"""Encabezado de las líneas de MONITOR. Empiezan con '#' para que no se
mezclen con las filas de datos de MEASURE al guardar el archivo."""


class Firmware:
    """Estado del firmware y atención de comandos."""

    def __init__(self):
        self.io = SerialIO()
        self.acq = Acquisition()
        self.run_ids = record.RunIdGenerator()
        self.sample_id = config.DEFAULT_SAMPLE_ID
        self.m = config.M_REPETITIONS
        self.warmup_s = config.WARMUP_S

    # ========================================================
    # Utilidades
    # ========================================================

    def now_ms(self):
        """Milisegundos desde que arrancó la Pico (para timestamp_ms)."""
        return time.ticks_ms()

    def elapsed_s(self, t0_ms):
        """Segundos transcurridos desde t0_ms."""
        return time.ticks_diff(time.ticks_ms(), t0_ms) / 1000

    def stop_requested(self):
        """Revisa, sin esperar, si el operador escribió algo durante una medición.

        Devuelve True si llegó STOP. Cualquier otro comando se rechaza,
        porque no se puede cambiar la configuración a mitad de una medición.
        """
        line = self.io.read_line()
        if line is None:
            return False
        r = parse_command(line)
        if r is None:
            return False
        if r["cmd"] == "STOP":
            self.io.info("STOP recibido")
            return True
        self.io.error("midiendo: solo se acepta STOP")
        return False

    def status_text(self):
        """Resumen de la configuración vigente, en una línea."""
        return "fw={} ID={} N={} FS={} M={} WARMUP={} SAT={}".format(
            config.FW_VERSION, self.sample_id, self.acq.n, self.acq.fs,
            self.m, self.warmup_s, config.SATURATION_THRESHOLD)

    # ========================================================
    # Comandos simples
    # ========================================================

    def cmd_hello(self):
        """Saluda, muestra la configuración y el encabezado CSV."""
        self.io.info("microplastic-detector " + self.status_text())
        self.io.send(config.CSV_HEADER)

    def cmd_set(self, args):
        """Aplica los parámetros de SET (ya validados por parse_command)."""
        if "ID" in args:
            self.sample_id = args["ID"]
        if "M" in args:
            self.m = args["M"]
        if "WARMUP" in args:
            self.warmup_s = args["WARMUP"]
        if "N" in args or "FS" in args:
            n = args.get("N", self.acq.n)
            fs = args.get("FS", self.acq.fs)
            self.acq.configure(n, fs)
            # record.py escribe config.FS_HZ en cada fila; se actualiza
            # para que el CSV refleje la frecuencia que realmente se usa.
            config.FS_HZ = fs
        self.io.info("OK " + self.status_text())

    # ========================================================
    # Calentamiento
    # ========================================================

    def warmup(self):
        """Repite dark/light durante self.warmup_s segundos sin guardar datos.

        Devuelve True si terminó, False si se canceló con STOP.
        """
        if self.warmup_s <= 0:
            return True
        self.io.info("CALENTANDO {} s (STOP para cancelar)".format(self.warmup_s))
        t0 = time.ticks_ms()
        next_report = WARMUP_REPORT_S
        while True:
            t = self.elapsed_s(t0)
            if t >= self.warmup_s:
                break
            dark, light = self.acq.measure_repetition()
            if self.stop_requested():
                return False
            t = self.elapsed_s(t0)
            if t >= next_report:
                s_d = stats.welford_block(dark)
                s_l = stats.welford_block(light)
                self.io.info("CALENTANDO {:.0f}/{} s  dV={:.1f}".format(
                    t, self.warmup_s, s_l["mu"] - s_d["mu"]))
                next_report += WARMUP_REPORT_S
        self.io.info("CALENTAMIENTO TERMINADO")
        return True

    # ========================================================
    # Medición completa
    # ========================================================

    def cmd_measure(self, is_baseline=False):
        """Calentamiento + M repeticiones + fila SUMMARY."""
        run_id = self.run_ids.next()
        self.io.info("INICIO {} ID={} M={} baseline={}".format(
            run_id, self.sample_id, self.m, 1 if is_baseline else 0))

        if not self.warmup():
            self.acq.shutdown()
            self.io.info("CANCELADO {} durante el calentamiento".format(run_id))
            return

        dv_values = []
        flags = []
        for rep in range(1, self.m + 1):
            dark, light = self.acq.measure_repetition()
            s_d = stats.welford_block(dark)
            s_l = stats.welford_block(light)
            dv = stats.delta_v_from_blocks(s_l, s_d)
            quality = stats.quality_flag(s_l, s_d)

            self.io.send(record.row_for_repetition(
                self.now_ms(), run_id, self.sample_id, rep,
                s_l, s_d, dv, quality, is_baseline))

            dv_values.append(dv["dV"])
            flags.append(quality)

            if self.stop_requested():
                self.acq.shutdown()
                self.io.info("CANCELADO {} en la repeticion {} (sin SUMMARY)".format(
                    run_id, rep))
                return

        summary = stats.summarize_repetitions(dv_values)
        global_quality = stats.combine_quality(flags)
        self.io.send(record.row_for_summary(
            self.now_ms(), run_id, self.sample_id, self.acq.n,
            summary, global_quality, is_baseline))
        self.io.info("FIN {} dV={:.2f} sem={:.3f} calidad={}".format(
            run_id, summary["mean_dV"], summary["sem_dV"], global_quality))

    # ========================================================
    # Monitor en vivo
    # ========================================================

    def cmd_monitor(self, seconds):
        """Muestra ΔV en vivo durante 'seconds' segundos (sin calentamiento).

        Útil para verificar la estabilización o la alineación óptica.
        Las líneas empiezan con '#MON' para no mezclarse con los datos.
        """
        self.io.info("MONITOR {} s (STOP para cancelar)".format(seconds))
        self.io.send(MONITOR_HEADER)
        t0 = time.ticks_ms()
        while self.elapsed_s(t0) < seconds:
            t = self.elapsed_s(t0)
            dark, light = self.acq.measure_repetition()
            s_d = stats.welford_block(dark)
            s_l = stats.welford_block(light)
            self.io.send("#MON,{:.1f},{:.1f},{:.1f},{:.1f},{:.1f}".format(
                t, s_d["mu"], s_l["mu"], s_l["mu"] - s_d["mu"], s_l["sigma"]))
            if self.stop_requested():
                break
        self.acq.shutdown()
        self.io.info("MONITOR TERMINADO")

    # ========================================================
    # Despacho de comandos y bucle principal
    # ========================================================

    def handle(self, line):
        """Interpreta una línea y ejecuta el comando correspondiente."""
        r = parse_command(line)
        if r is None:
            return
        cmd = r["cmd"]
        if cmd == "ERROR":
            self.io.error(r["msg"])
        elif cmd == "HELLO":
            self.cmd_hello()
        elif cmd == "HELP":
            self.io.info(HELP_TEXT)
        elif cmd == "STATUS":
            self.io.info(self.status_text())
        elif cmd == "SET":
            self.cmd_set(r["args"])
        elif cmd == "MEASURE":
            self.cmd_measure(is_baseline=False)
        elif cmd == "BASELINE":
            self.cmd_measure(is_baseline=True)
        elif cmd == "MONITOR":
            self.cmd_monitor(r["args"]["SEGUNDOS"])
        elif cmd == "STOP":
            self.io.info("no hay ninguna medicion en curso")

    def run(self):
        """Bucle principal: espera comandos y los atiende uno a uno."""
        self.cmd_hello()
        self.io.info("listo. Escribe HELP para ver los comandos")
        while True:
            line = self.io.read_line()
            if line is None:
                # Nada que hacer: pausa corta para no ocupar el procesador.
                # Esta espera está FUERA de la adquisición, por eso se permite.
                time.sleep_ms(10)
                continue
            try:
                self.handle(line)
            except Exception as e:
                # Cualquier falla se informa y el firmware sigue vivo
                self.acq.shutdown()
                self.io.error("{}: {}".format(type(e).__name__, e))


def main():
    """Punto de entrada. Garantiza que el LED quede apagado al salir."""
    fw = Firmware()
    try:
        fw.run()
    finally:
        fw.acq.shutdown()