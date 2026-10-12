"""
io_serial.py — Capa 4a: comunicación por USB serial
===================================================

Dos responsabilidades separadas:

1. parse_command(line): convierte un texto escrito por el operador
   (por ejemplo "SET ID=agua_01 M=5") en un diccionario que main.py
   entiende, validando cada valor. Es lógica pura: se prueba con
   pytest en el PC.

2. SerialIO: lee líneas del puerto USB SIN BLOQUEAR el programa
   (para poder recibir STOP mientras se mide) y envía líneas.
   Solo funciona en la Pico.

Convención de salida:
- Filas de datos: CSV normal.
- Mensajes: empiezan con '#'. Así un análisis posterior puede
  ignorarlos (por ejemplo pandas.read_csv(..., comment="#")).

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import sys


# ============================================================
# 1. COMANDOS Y LÍMITES
# ============================================================

COMMANDS = ("HELLO", "HELP", "STATUS", "SET", "MEASURE",
            "BASELINE", "MONITOR", "STOP")
"""Comandos que acepta el firmware."""

SET_LIMITS = {
    "N": (2, 5000),        # muestras por bloque
    "FS": (1, 10000),      # Hz (máximo que adq.py mantiene con precisión)
    "M": (1, 100),         # repeticiones por medición
    "WARMUP": (0, 1800),   # segundos de calentamiento (0 = sin calentamiento)
}
"""Rango permitido (mínimo, máximo) para cada parámetro numérico de SET."""

ID_MAX_LEN = 32
"""Longitud máxima del ID de muestra."""

MONITOR_DEFAULT_S = 60
"""Duración por defecto de MONITOR, en segundos."""

MONITOR_MAX_S = 3600
"""Duración máxima de MONITOR, en segundos."""

HELP_TEXT = (
    "HELLO | HELP | STATUS | SET ID=x N=n FS=n M=n WARMUP=s | "
    "MEASURE | BASELINE | MONITOR [s] | STOP"
)


# ============================================================
# 2. PARSER DE COMANDOS (lógica pura, testeable en PC)
# ============================================================

def _error(msg):
    """Construye el diccionario de error que devuelve parse_command."""
    return {"cmd": "ERROR", "msg": msg}


def _is_valid_id(text):
    """True si el ID solo tiene letras, números, '_' o '-' y no es muy largo.

    Se prohíben comas y espacios porque romperían el formato CSV.
    """
    if len(text) == 0 or len(text) > ID_MAX_LEN:
        return False
    for ch in text:
        if not (ch.isalpha() or ch.isdigit() or ch in "_-"):
            return False
    return True


def _parse_int(text):
    """Convierte un texto a entero. Devuelve None si no es un entero válido."""
    if len(text) == 0:
        return None
    body = text[1:] if text[0] == "-" else text
    if len(body) == 0 or not body.isdigit():
        return None
    return int(text)


def parse_command(line):
    """Interpreta una línea de texto escrita por el operador.

    Parámetros
    ----------
    line : str — texto recibido por el puerto serial (sin importar
                 mayúsculas/minúsculas en el comando).

    Devuelve
    --------
    None si la línea está vacía, o un dict con:
        {"cmd": "HELLO"}                          comandos sin argumentos
        {"cmd": "SET", "args": {"ID": "agua_01", "M": 5}}
        {"cmd": "MONITOR", "args": {"SEGUNDOS": 120}}
        {"cmd": "ERROR", "msg": "explicación"}    si algo no es válido

    En SET, las claves se pasan a mayúsculas y los valores numéricos
    se convierten a int y se validan con SET_LIMITS. El ID conserva
    las mayúsculas/minúsculas que escribió el operador.
    """
    line = line.strip()
    if len(line) == 0:
        return None

    tokens = line.split()
    cmd = tokens[0].upper()
    rest = tokens[1:]

    if cmd not in COMMANDS:
        return _error("comando desconocido: {}. Escribe HELP".format(tokens[0]))

    # --- SET: uno o varios pares CLAVE=VALOR ---
    if cmd == "SET":
        if len(rest) == 0:
            return _error("SET necesita al menos un parametro, ej. SET ID=agua_01")
        args = {}
        for tok in rest:
            if "=" not in tok:
                return _error("formato invalido '{}', use CLAVE=VALOR".format(tok))
            key, value = tok.split("=", 1)
            key = key.upper()
            if key == "ID":
                if not _is_valid_id(value):
                    return _error("ID invalido: solo letras, numeros, _ o -, "
                                  "maximo {} caracteres".format(ID_MAX_LEN))
                args["ID"] = value
            elif key in SET_LIMITS:
                num = _parse_int(value)
                if num is None:
                    return _error("{} debe ser un numero entero".format(key))
                lo, hi = SET_LIMITS[key]
                if num < lo or num > hi:
                    return _error("{} fuera de rango ({} a {})".format(key, lo, hi))
                args[key] = num
            else:
                return _error("parametro desconocido: {}".format(key))
        return {"cmd": "SET", "args": args}

    # --- MONITOR: duración opcional en segundos ---
    if cmd == "MONITOR":
        if len(rest) == 0:
            return {"cmd": "MONITOR", "args": {"SEGUNDOS": MONITOR_DEFAULT_S}}
        if len(rest) > 1:
            return _error("uso: MONITOR [segundos]")
        num = _parse_int(rest[0])
        if num is None or num < 1 or num > MONITOR_MAX_S:
            return _error("MONITOR: segundos entre 1 y {}".format(MONITOR_MAX_S))
        return {"cmd": "MONITOR", "args": {"SEGUNDOS": num}}

    # --- El resto de comandos no llevan argumentos ---
    if len(rest) > 0:
        return _error("{} no lleva parametros".format(cmd))
    return {"cmd": cmd}


# ============================================================
# 3. ENTRADA / SALIDA POR USB (solo en la Pico)
# ============================================================

class SerialIO:
    """Lectura no bloqueante y escritura de líneas por USB serial.

    Uso típico en main.py:
        io = SerialIO()
        line = io.read_line()     # devuelve una línea o None, nunca se queda esperando
        io.send("12345,R001,...") # fila de datos
        io.info("CALENTANDO 60/180 s")
        io.error("comando desconocido")
    """

    MAX_LINE = 200
    """Si llega una línea más larga que esto sin salto de línea, se descarta."""

    def __init__(self):
        # Se importa aquí (y no arriba) para que el parser se pueda
        # probar en Windows, donde select.poll no existe.
        import select
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)
        self._buf = ""

    def read_line(self):
        """Devuelve una línea completa si ya llegó, o None si no hay nada.

        Nunca se queda esperando: lee solo los caracteres que ya están
        disponibles y los acumula hasta encontrar un salto de línea.
        """
        while self._poll.poll(0):
            ch = sys.stdin.read(1)
            if ch == "\n" or ch == "\r":
                if len(self._buf) > 0:
                    line = self._buf
                    self._buf = ""
                    return line
            else:
                self._buf += ch
                if len(self._buf) > self.MAX_LINE:
                    self._buf = ""  # protección contra basura en el puerto
        return None

    def send(self, line):
        """Envía una línea de datos (fila CSV)."""
        print(line)

    def info(self, msg):
        """Envía un mensaje informativo, marcado con '#'."""
        print("# " + msg)

    def error(self, msg):
        """Envía un mensaje de error, marcado con '#ERROR'."""
        print("#ERROR " + msg)