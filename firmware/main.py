"""
main.py — Orquestación del firmware
====================================

Junta todas las capas:
    io_serial  →  recibe comandos del operador por USB
    io_wifi    →  (opcional) recibe comandos desde la página del celular
    adq        →  controla el LED y adquiere bloques
    stats      →  calcula media, sigma, sem, ΔV y calidad
    record     →  arma las filas CSV
    Output     →  envía filas y mensajes por USB y, con WiFi, también al
                  archivo de la sesión y a la página (session.py)

Flujo de una medición (comando MEASURE o BASELINE):
    1. Calentamiento: repite dark/light durante WARMUP segundos sin
       guardar datos, para que el LED llegue a su equilibrio térmico.
       Cada 30 s informa cómo va ΔV.
    2. M repeticiones: una fila CSV por repetición.
    3. Fila SUMMARY con el promedio y la dispersión de las M repeticiones.
    En cualquier momento se puede cancelar con STOP (por USB o desde la página).

Con WiFi (config.WIFI_ENABLED = True), el servidor web recibe un turno en
los mismos puntos donde se revisa STOP: en espera cada 10 ms y, durante una
medición, entre repeticiones. Nunca dentro de un bloque de muestras.

Para correrlo desde Thonny:
    from firmware.main import main
    main()
Para que arranque solo al conectar la Pico: copiar pico/main.py a la raíz.

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import time

from firmware import config
from firmware import stats
from firmware import record
from firmware.adq import Acquisition
from firmware.io_serial import SerialIO, parse_command, HELP_TEXT
from firmware.session import (Session, KIND_WARMUP, KIND_REPETITION,
                              KIND_MONITOR)


WARMUP_REPORT_S = 30
"""Cada cuántos segundos se informa el avance del calentamiento."""

MONITOR_HEADER = "#MON,t_s,mu_dark,mu_light,dV,sigma_light"
"""Encabezado de las líneas de MONITOR. Empiezan con '#' para que no se
mezclen con las filas de datos de MEASURE al guardar el archivo."""


class Output:
    """Salida del firmware: USB siempre; archivo de sesión y página si hay WiFi.

    Tiene los mismos métodos que SerialIO (read_line, send, info, error),
    así el resto de main.py no cambia: donde antes se llamaba a SerialIO
    ahora se llama a Output, y Output reparte cada línea.
    """

    def __init__(self, serial, session, log=None):
        self.serial = serial
        self.session = session
        self.log = log

    def read_line(self):
        return self.serial.read_line()

    def _to_log(self, line):
        """Copia la línea al archivo; si falla (memoria llena), deja de copiar."""
        if self.log is None:
            return
        try:
            self.log.write(line)
        except OSError as e:
            self.log = None
            self.serial.error("no se pudo escribir el archivo de sesion: {}".format(e))

    def send(self, line):
        """Fila de datos (CSV o #MON): USB y archivo."""
        self.serial.send(line)
        self._to_log(line)

    def info(self, msg):
        """Mensaje '# ...': USB, archivo y lista de mensajes de la página."""
        self.serial.info(msg)
        self._to_log("# " + msg)
        self.session.add_msg(msg)

    def error(self, msg):
        """Mensaje '#ERROR ...': USB, archivo y lista de mensajes de la página."""
        self.serial.error(msg)
        self._to_log("#ERROR " + msg)
        self.session.add_msg("ERROR " + msg)


class Firmware:
    """Estado del firmware y atención de comandos."""

    def __init__(self):
        self.session = Session(config.FW_VERSION, config.T_REL_THRESHOLD,
                               config.WEB_SERIES_POINTS, config.WEB_MAX_MSGS)
        self.io = Output(SerialIO(), self.session)
        self.web = None   # WebServer, solo si el WiFi arranca bien
        self.acq = Acquisition()
        self.run_ids = record.RunIdGenerator()
        self.sample_id = config.DEFAULT_SAMPLE_ID
        self.session.set_sample_id(self.sample_id)
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
        if line is None and self.web is not None:
            # La página solo puede mandar STOP mientras se mide
            # (io_wifi rechaza lo demás y se lo explica al celular).
            line = self.web.poll(busy=True)
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
    # WiFi (opcional)
    # ========================================================

    def start_wifi(self):
        """Crea la red, el archivo de la sesión y el servidor web.

        Si algo falla, lo informa con #ERROR y el firmware sigue por USB
        como siempre: el WiFi nunca debe impedir medir.
        """
        if not config.WIFI_ENABLED:
            return
        try:
            from firmware import secrets
            password = secrets.WIFI_AP_PASSWORD
        except (ImportError, AttributeError):
            self.io.error("WiFi apagado: falta firmware/secrets.py con WIFI_AP_PASSWORD "
                          "(copiar secrets_ejemplo.py)")
            return
        if len(password) < config.WIFI_AP_PASSWORD_MIN_LEN:
            self.io.error("WiFi apagado: la clave debe tener al menos {} caracteres".format(
                config.WIFI_AP_PASSWORD_MIN_LEN))
            return

        # Imports aquí: si el WiFi está apagado, no se cargan (ahorra memoria)
        from firmware.io_wifi import SessionLog, WebServer

        log = None
        try:
            log = SessionLog(config.SESSION_DIR)
            self.io.log = log
        except OSError as e:
            self.io.error("sin archivo de sesion en la Pico: {}".format(e))

        web = WebServer(self.session, log)
        try:
            ip = web.start(config.WIFI_AP_SSID, password, config.WEB_PORT)
        except Exception as e:
            self.io.error("WiFi apagado: {}: {}".format(type(e).__name__, e))
            return
        self.web = web
        self.io.info("WIFI red={} pagina=http://{} archivo={}".format(
            config.WIFI_AP_SSID, ip, log.path if log is not None else "-"))

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
            self.session.set_sample_id(self.sample_id)
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
            t = self.elapsed_s(t0)
            self.session.update_elapsed(t)
            report = t >= next_report
            # Con WiFi se calcula ΔV en cada repetición para la gráfica;
            # sin WiFi, solo cada 30 s (igual que en la campaña).
            if report or self.web is not None:
                s_d = stats.welford_block(dark)
                s_l = stats.welford_block(light)
                dv = s_l["mu"] - s_d["mu"]
                self.session.add_point(dv, KIND_WARMUP, s_d["mu"], s_l["mu"], s_l["sigma"])
            if self.stop_requested():
                return False
            if report:
                self.io.info("CALENTANDO {:.0f}/{} s  dV={:.1f}".format(
                    t, self.warmup_s, dv))
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
        self.session.start_warmup(run_id, is_baseline, self.warmup_s, self.m)

        if not self.warmup():
            self.acq.shutdown()
            self.session.to_idle()
            self.io.info("CANCELADO {} durante el calentamiento".format(run_id))
            return

        self.session.start_measure()
        dv_values = []
        flags = []
        for rep in range(1, self.m + 1):
            self.session.set_rep(rep)
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
            self.session.add_point(dv["dV"], KIND_REPETITION,
                                   s_d["mu"], s_l["mu"], s_l["sigma"])

            if self.stop_requested():
                self.acq.shutdown()
                self.session.to_idle()
                self.io.info("CANCELADO {} en la repeticion {} (sin SUMMARY)".format(
                    run_id, rep))
                return

        summary = stats.summarize_repetitions(dv_values)
        global_quality = stats.combine_quality(flags)
        self.io.send(record.row_for_summary(
            self.now_ms(), run_id, self.sample_id, self.acq.n,
            summary, global_quality, is_baseline))
        self.session.add_result(run_id, self.sample_id, summary["mean_dV"],
                                summary["sem_dV"], global_quality, is_baseline)
        self.session.to_idle()
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
        self.session.start_monitor(seconds)
        t0 = time.ticks_ms()
        while self.elapsed_s(t0) < seconds:
            t = self.elapsed_s(t0)
            dark, light = self.acq.measure_repetition()
            s_d = stats.welford_block(dark)
            s_l = stats.welford_block(light)
            dv = s_l["mu"] - s_d["mu"]
            self.io.send("#MON,{:.1f},{:.1f},{:.1f},{:.1f},{:.1f}".format(
                t, s_d["mu"], s_l["mu"], dv, s_l["sigma"]))
            self.session.update_elapsed(self.elapsed_s(t0))
            self.session.add_point(dv, KIND_MONITOR, s_d["mu"], s_l["mu"], s_l["sigma"])
            if self.stop_requested():
                break
        self.acq.shutdown()
        self.session.to_idle()
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
        """Bucle principal: espera comandos (USB o página) y los atiende uno a uno."""
        self.start_wifi()
        self.cmd_hello()
        self.io.info("listo. Escribe HELP para ver los comandos")
        while True:
            line = self.io.read_line()
            if line is None and self.web is not None:
                line = self.web.poll(busy=False)
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
                self.session.to_idle()
                self.io.error("{}: {}".format(type(e).__name__, e))


def main():
    """Punto de entrada. Garantiza que el LED quede apagado al salir."""
    fw = Firmware()
    try:
        fw.run()
    finally:
        fw.acq.shutdown()