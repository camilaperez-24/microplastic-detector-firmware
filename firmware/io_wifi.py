"""
io_wifi.py — Capa 4b: red WiFi y página web
============================================

La Pico crea su propia red WiFi (modo punto de acceso) y atiende la
página del celular en http://192.168.4.1. La página es "otro teclado":
sus botones mandan los mismos comandos que se escriben en Thonny.

Tres partes separadas:

1. Funciones puras (PC y Pico, con tests en tests/test_io_wifi.py):
   leer una petición HTTP, armar los encabezados de la respuesta,
   validar el comando que manda la página y elegir el nombre del
   archivo de la sesión.

2. SessionLog (solo Pico): copia en un archivo de la Pico todo lo que
   sale por USB (/datos/sesion_NNN.csv, uno por cada arranque), con el
   mismo formato de la Shell de Thonny.

3. WebServer (solo Pico): crea la red y atiende las peticiones SIN
   bloquear. main.py le da un turno con poll() en los mismos puntos
   donde revisa si llegó STOP: en espera cada 10 ms y, durante una
   medición, entre repeticiones. Nunca dentro de un bloque de muestras.

Rutas (contrato completo en docs/plan_wifi.md, sección 4):
    GET  /            la página (firmware/web/index.html)
    GET  /api/estado  estado de la sesión en JSON (session.py)
    POST /api/cmd     un comando en texto plano, p. ej. "MEASURE"
    GET  /api/csv     el archivo de la sesión

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import json

from firmware import config
from firmware.io_serial import parse_command


# ============================================================
# 1. CONSTANTES HTTP
# ============================================================

HEADER_END = b"\r\n\r\n"
"""Línea en blanco que separa los encabezados del cuerpo."""

MAX_HEAD_BYTES = 2048
"""Encabezados más largos que esto se rechazan (protege la memoria)."""

MAX_BODY_BYTES = 256
"""Un comando nunca es tan largo; cuerpos mayores se rechazan."""

MAX_COMMAND_LEN = 200
"""Mismo límite de línea que SerialIO.MAX_LINE."""

CHUNK_BYTES = 1024
"""Tamaño de cada pedazo al enviar archivos (página y CSV)."""

STATUS_TEXT = {
    200: "OK",
    204: "No Content",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    413: "Payload Too Large",
    431: "Request Header Fields Too Large",
    500: "Internal Server Error",
}

SESSION_PREFIX = "sesion_"
SESSION_SUFFIX = ".csv"


# ============================================================
# 2. FUNCIONES PURAS (testeables en PC)
# ============================================================

def split_request(raw):
    """Separa una petición en (encabezados, cuerpo).

    raw: bytes recibidos hasta ahora.
    Devuelve None si todavía no llegó la línea en blanco del final
    de los encabezados.
    """
    idx = raw.find(HEADER_END)
    if idx < 0:
        return None
    return raw[:idx], raw[idx + len(HEADER_END):]


def parse_request_head(head):
    """Interpreta la línea de petición y los encabezados.

    head: bytes, sin la línea en blanco final.
    Devuelve None si está mal formada, o un dict:
        {"method": "GET", "path": "/api/estado", "query": "",
         "headers": {"content-length": "7", ...}}   (claves en minúscula)
    """
    try:
        text = head.decode()
    except (UnicodeError, ValueError):
        return None
    lines = text.split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) != 3 or not parts[2].startswith("HTTP/"):
        return None
    method = parts[0].upper()
    target = parts[1]
    if len(method) == 0 or not target.startswith("/"):
        return None
    if "?" in target:
        path, query = target.split("?", 1)
    else:
        path, query = target, ""
    headers = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    return {"method": method, "path": path, "query": query, "headers": headers}


def content_length(headers):
    """Valor de Content-Length como entero (0 si no viene).

    Devuelve None si el valor no es un entero válido o es negativo.
    """
    value = headers.get("content-length", "0")
    if len(value) == 0 or not value.isdigit():
        return None
    return int(value)


def build_head(code, content_type=None, length=None):
    """Arma los encabezados de una respuesta HTTP.

    Siempre cierra la conexión y pide no guardar en caché: la página
    pregunta el estado cada ~1.5 s y siempre necesita el valor nuevo.
    """
    lines = ["HTTP/1.1 {} {}".format(code, STATUS_TEXT.get(code, "OK"))]
    if content_type is not None:
        lines.append("Content-Type: " + content_type)
    if length is not None:
        lines.append("Content-Length: {}".format(length))
    lines.append("Cache-Control: no-store")
    lines.append("Connection: close")
    return ("\r\n".join(lines) + "\r\n\r\n").encode()


def clean_command(body):
    """Convierte el cuerpo de POST /api/cmd en una línea de comando.

    Devuelve None si está vacío, no es texto, trae varias líneas
    o es demasiado largo.
    """
    try:
        text = body.decode()
    except (UnicodeError, ValueError):
        return None
    text = text.strip()
    if len(text) == 0 or len(text) > MAX_COMMAND_LEN:
        return None
    if "\n" in text or "\r" in text:
        return None
    return text


def check_web_command(body, busy):
    """Valida un comando que llega desde la página.

    Usa el mismo parse_command() de la entrada por USB, así que valen
    las mismas reglas y los mismos mensajes de error.

    Parámetros
    ----------
    body : bytes — cuerpo de la petición POST /api/cmd.
    busy : bool  — True si hay una medición o un monitor en curso.

    Devuelve
    --------
    (True, linea)    si el comando es válido y se puede ejecutar ya.
    (False, mensaje) si no.
    """
    line = clean_command(body)
    if line is None:
        return False, "comando vacio o invalido"
    r = parse_command(line)
    if r is None:
        return False, "comando vacio"
    if r["cmd"] == "ERROR":
        return False, r["msg"]
    if busy and r["cmd"] != "STOP":
        return False, "midiendo: solo se acepta STOP"
    return True, line


def next_session_name(existing):
    """Nombre del siguiente archivo de sesión.

    existing: nombres que ya hay en la carpeta (os.listdir).
    Ejemplo: ["sesion_001.csv", "sesion_007.csv"] → "sesion_008.csv".
    Se ignoran los archivos que no siguen el patrón.
    """
    highest = 0
    for name in existing:
        if not (name.startswith(SESSION_PREFIX) and name.endswith(SESSION_SUFFIX)):
            continue
        number = name[len(SESSION_PREFIX):-len(SESSION_SUFFIX)]
        if number.isdigit():
            highest = max(highest, int(number))
    return "{}{:03d}{}".format(SESSION_PREFIX, highest + 1, SESSION_SUFFIX)


# ============================================================
# 3. ARCHIVO DE LA SESIÓN (solo en la Pico)
# ============================================================

class SessionLog:
    """Copia en un archivo de la Pico todo lo que sale por USB.

    Uso típico:
        log = SessionLog("/datos")
        log.write("710386,R003,llenado_02,...")
        log.write("# FIN R003 ...")
    """

    def __init__(self, folder):
        """Crea la carpeta si no existe y abre un archivo nuevo.

        Lanza OSError si no se puede crear (por ejemplo, memoria llena).
        """
        import os
        try:
            os.mkdir(folder)
        except OSError:
            pass  # la carpeta ya existe
        self.path = folder + "/" + next_session_name(os.listdir(folder))
        self._f = open(self.path, "w")

    def write(self, line):
        """Agrega una línea y la guarda de inmediato (por si se va la luz)."""
        if self._f is None:
            return
        self._f.write(line)
        self._f.write("\n")
        self._f.flush()

    def close(self):
        """Cierra el archivo (para poder leerlo completo y enviarlo)."""
        if self._f is not None:
            self._f.close()
            self._f = None

    def reopen(self):
        """Vuelve a abrir el archivo para seguir agregando líneas."""
        if self._f is None:
            self._f = open(self.path, "a")


# ============================================================
# 4. SERVIDOR WEB (solo en la Pico)
# ============================================================

class WebServer:
    """Red WiFi propia + servidor HTTP que no bloquea.

    Uso típico en main.py:
        web = WebServer(session, log)
        ip = web.start("Detector-PE", "contraseña", 80)
        ...
        line = web.poll(busy=False)   # devuelve un comando o None
    """

    def __init__(self, session, log=None):
        """
        Parámetros
        ----------
        session : Session    — estado que se envía en /api/estado.
        log     : SessionLog — archivo que se envía en /api/csv (o None).
        """
        self.session = session
        self.log = log
        self.ip = None
        self._ap = None
        self._sock = None

    # --------------------------------------------------------
    # Arranque
    # --------------------------------------------------------

    def start(self, ssid, password, port):
        """Crea la red WiFi y abre el puerto. Devuelve la IP de la Pico.

        Lanza OSError o RuntimeError si algo falla; main.py lo informa
        con #ERROR y sigue sin WiFi (el firmware no se cae).
        """
        import network
        import socket
        import time

        ap = network.WLAN(network.AP_IF)
        # Los nombres de los parámetros cambiaron entre versiones de
        # MicroPython; se prueban en orden hasta que uno funcione.
        for kwargs in ({"ssid": ssid, "key": password},
                       {"ssid": ssid, "password": password},
                       {"essid": ssid, "password": password}):
            try:
                ap.config(**kwargs)
                break
            except (TypeError, ValueError):
                continue
        else:
            raise RuntimeError("no se pudo configurar el nombre y la clave de la red")
        ap.active(True)

        t0 = time.ticks_ms()
        while not ap.active():
            if time.ticks_diff(time.ticks_ms(), t0) > 5000:
                raise RuntimeError("la red WiFi no arranco en 5 s")
            time.sleep_ms(100)   # fuera de la adquisición: aquí sí se permite
        self._ap = ap
        self.ip = ap.ifconfig()[0]

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(socket.getaddrinfo("0.0.0.0", port)[0][-1])
        sock.listen(2)
        sock.setblocking(False)   # accept() no se queda esperando
        self._sock = sock
        return self.ip

    # --------------------------------------------------------
    # Turno del servidor
    # --------------------------------------------------------

    def poll(self, busy):
        """Atiende las peticiones que ya llegaron, sin esperar a nuevas.

        Parámetros
        ----------
        busy : bool — True si hay una medición o un monitor en curso
                      (entonces solo se acepta STOP).

        Devuelve
        --------
        str con el comando para main.py (p. ej. "MEASURE"), o None.
        Como mucho devuelve UN comando por turno: si la página manda
        SET y luego MEASURE, el segundo espera al siguiente turno y
        se ejecutan en orden.
        """
        if self._sock is None:
            return None
        for _ in range(config.WEB_MAX_REQUESTS_PER_POLL):
            try:
                client, _addr = self._sock.accept()
            except OSError:
                return None   # no hay conexiones pendientes
            command = None
            try:
                command = self._handle(client, busy)
            except OSError:
                # Celular que se desconectó o conexión abierta "por si acaso"
                # sin pedir nada (los navegadores lo hacen): se ignora.
                pass
            except Exception as e:
                # Un cliente que falla nunca debe tumbar el firmware
                self.session.add_msg("ERROR web: {}: {}".format(type(e).__name__, e))
            finally:
                try:
                    client.close()
                except OSError:
                    pass
            if command is not None:
                return command
        return None

    # --------------------------------------------------------
    # Atención de una petición
    # --------------------------------------------------------

    def _handle(self, client, busy):
        """Lee una petición, responde y devuelve un comando o None."""
        client.settimeout(config.WEB_CLIENT_TIMEOUT_S)

        raw = b""
        parts = None
        while parts is None:
            chunk = client.recv(512)
            if not chunk:
                return None   # el cliente cerró sin pedir nada
            raw += chunk
            if len(raw) > MAX_HEAD_BYTES:
                self._send_text(client, 431, "encabezados muy largos")
                return None
            parts = split_request(raw)
        head, body = parts

        req = parse_request_head(head)
        if req is None:
            self._send_text(client, 400, "peticion mal formada")
            return None
        length = content_length(req["headers"])
        if length is None:
            self._send_text(client, 400, "Content-Length invalido")
            return None
        if length > MAX_BODY_BYTES:
            self._send_text(client, 413, "cuerpo muy largo")
            return None
        while len(body) < length:
            chunk = client.recv(length - len(body))
            if not chunk:
                break
            body += chunk

        method = req["method"]
        path = req["path"]
        if path == "/api/cmd":
            if method != "POST":
                self._send_text(client, 405, "use POST")
                return None
            ok, value = check_web_command(body[:length], busy)
            if not ok:
                self._send_json(client, {"ok": False, "msg": value})
                return None
            # Se responde ANTES de ejecutar: MEASURE dura minutos
            self._send_json(client, {"ok": True})
            return value
        if method != "GET":
            self._send_text(client, 405, "metodo no permitido")
        elif path == "/" or path == "/index.html":
            self._send_page(client)
        elif path == "/api/estado":
            self._send_json(client, self.session.to_dict())
        elif path == "/api/csv":
            self._send_csv(client)
        elif path == "/favicon.ico":
            self._send_all(client, build_head(204))
        else:
            self._send_text(client, 404, "no existe: " + path)
        return None

    # --------------------------------------------------------
    # Envío
    # --------------------------------------------------------

    def _send_all(self, client, data):
        """Envía todos los bytes (send() puede enviar solo una parte)."""
        view = memoryview(data)
        sent = 0
        while sent < len(data):
            n = client.send(view[sent:])
            if not n:
                raise OSError("envio incompleto")
            sent += n

    def _send_text(self, client, code, text):
        body = text.encode()
        self._send_all(client, build_head(code, "text/plain; charset=utf-8", len(body)))
        self._send_all(client, body)

    def _send_json(self, client, data):
        body = json.dumps(data).encode()
        self._send_all(client, build_head(200, "application/json", len(body)))
        self._send_all(client, body)

    def _send_file(self, client, path, content_type):
        """Envía un archivo de la Pico por pedazos (no lo carga entero en RAM)."""
        import os
        try:
            size = os.stat(path)[6]
        except OSError:
            self._send_text(client, 404, "no existe el archivo " + path)
            return
        self._send_all(client, build_head(200, content_type, size))
        buf = bytearray(CHUNK_BYTES)
        with open(path, "rb") as f:
            while True:
                n = f.readinto(buf)
                if not n:
                    break
                self._send_all(client, memoryview(buf)[:n])

    def _send_page(self, client):
        self._send_file(client, config.WEB_PAGE_PATH, "text/html; charset=utf-8")

    def _send_csv(self, client):
        """Envía el archivo de la sesión. Se cierra un momento para leerlo completo."""
        if self.log is None:
            self._send_text(client, 404, "no hay archivo de sesion")
            return
        self.log.close()
        try:
            self._send_file(client, self.log.path, "text/csv; charset=utf-8")
        finally:
            self.log.reopen()
