"""
test_io_serial.py — Tests del parser de comandos
=================================================

Valida parse_command() de firmware/io_serial.py en el PC.
La clase SerialIO NO se prueba aquí porque solo funciona en la Pico.

Para correr:
    pytest -v tests/test_io_serial.py

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

from firmware import io_serial
from firmware.io_serial import parse_command


class TestComandosSimples:
    """Comandos sin argumentos."""

    def test_hello(self):
        assert parse_command("HELLO") == {"cmd": "HELLO"}

    def test_minusculas_y_espacios(self):
        """El operador puede escribir en minúsculas y con espacios extra."""
        assert parse_command("  measure  ") == {"cmd": "MEASURE"}

    def test_todos_los_comandos_sin_argumentos(self):
        for c in ("HELLO", "HELP", "STATUS", "MEASURE", "BASELINE", "STOP"):
            assert parse_command(c) == {"cmd": c}

    def test_linea_vacia_devuelve_none(self):
        assert parse_command("") is None
        assert parse_command("   ") is None

    def test_comando_desconocido(self):
        r = parse_command("BAILAR")
        assert r["cmd"] == "ERROR"
        assert "desconocido" in r["msg"]

    def test_comando_simple_con_argumento_sobrante(self):
        r = parse_command("MEASURE ahora")
        assert r["cmd"] == "ERROR"


class TestSet:
    """Comando SET con uno o varios parámetros."""

    def test_set_id(self):
        assert parse_command("SET ID=agua_limpia_01") == {
            "cmd": "SET", "args": {"ID": "agua_limpia_01"}}

    def test_id_conserva_mayusculas(self):
        r = parse_command("set id=PE_Muestra-3")
        assert r["args"]["ID"] == "PE_Muestra-3"

    def test_varios_parametros(self):
        r = parse_command("SET N=500 FS=2000 M=5 WARMUP=0")
        assert r == {"cmd": "SET",
                     "args": {"N": 500, "FS": 2000, "M": 5, "WARMUP": 0}}

    def test_valores_numericos_son_int(self):
        r = parse_command("SET M=10")
        assert isinstance(r["args"]["M"], int)

    def test_set_sin_parametros(self):
        assert parse_command("SET")["cmd"] == "ERROR"

    def test_formato_sin_igual(self):
        assert parse_command("SET M10")["cmd"] == "ERROR"

    def test_parametro_desconocido(self):
        r = parse_command("SET COLOR=rojo")
        assert r["cmd"] == "ERROR"
        assert "desconocido" in r["msg"]

    def test_numero_no_entero(self):
        assert parse_command("SET M=abc")["cmd"] == "ERROR"
        assert parse_command("SET M=2.5")["cmd"] == "ERROR"
        assert parse_command("SET M=")["cmd"] == "ERROR"

    def test_fuera_de_rango(self):
        assert parse_command("SET M=0")["cmd"] == "ERROR"
        assert parse_command("SET FS=20000")["cmd"] == "ERROR"
        assert parse_command("SET N=1")["cmd"] == "ERROR"
        assert parse_command("SET WARMUP=-5")["cmd"] == "ERROR"

    def test_limites_exactos_son_validos(self):
        for key, (lo, hi) in io_serial.SET_LIMITS.items():
            assert parse_command("SET {}={}".format(key, lo))["cmd"] == "SET"
            assert parse_command("SET {}={}".format(key, hi))["cmd"] == "SET"

    def test_id_con_coma_rechazado(self):
        """Una coma en el ID rompería el CSV."""
        assert parse_command("SET ID=agua,limpia")["cmd"] == "ERROR"

    def test_id_vacio_o_muy_largo(self):
        assert parse_command("SET ID=")["cmd"] == "ERROR"
        largo = "a" * (io_serial.ID_MAX_LEN + 1)
        assert parse_command("SET ID=" + largo)["cmd"] == "ERROR"

    def test_un_error_invalida_todo_el_set(self):
        """Si un parámetro está mal, no se aplica ninguno."""
        r = parse_command("SET ID=agua_01 M=999")
        assert r["cmd"] == "ERROR"


class TestMonitor:
    """Comando MONITOR con duración opcional."""

    def test_sin_duracion_usa_default(self):
        r = parse_command("MONITOR")
        assert r == {"cmd": "MONITOR",
                     "args": {"SEGUNDOS": io_serial.MONITOR_DEFAULT_S}}

    def test_con_duracion(self):
        assert parse_command("monitor 120")["args"]["SEGUNDOS"] == 120

    def test_duracion_invalida(self):
        assert parse_command("MONITOR 0")["cmd"] == "ERROR"
        assert parse_command("MONITOR abc")["cmd"] == "ERROR"
        assert parse_command("MONITOR 10 20")["cmd"] == "ERROR"
        assert parse_command("MONITOR 999999")["cmd"] == "ERROR"