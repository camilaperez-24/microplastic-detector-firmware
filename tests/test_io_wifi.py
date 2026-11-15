"""
test_io_wifi.py — Tests de la parte pura del servidor web
==========================================================

Valida en el PC las funciones puras de firmware/io_wifi.py: lectura de
peticiones HTTP, encabezados de respuesta, validación de los comandos
que manda la página y nombre del archivo de la sesión.
SessionLog y WebServer NO se prueban aquí porque solo funcionan en la Pico.

Para correr:
    pytest -v tests/test_io_wifi.py

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

from firmware.io_wifi import (
    build_head,
    check_web_command,
    clean_command,
    content_length,
    next_session_name,
    parse_request_head,
    split_request,
)


class TestSplitRequest:
    def test_peticion_completa(self):
        raw = b"POST /api/cmd HTTP/1.1\r\nContent-Length: 7\r\n\r\nMEASURE"
        head, body = split_request(raw)
        assert head == b"POST /api/cmd HTTP/1.1\r\nContent-Length: 7"
        assert body == b"MEASURE"

    def test_encabezados_incompletos(self):
        """Si aún no llega la línea en blanco, hay que seguir leyendo."""
        assert split_request(b"GET / HTTP/1.1\r\nHost: 192.168.4.1\r\n") is None

    def test_cuerpo_vacio(self):
        head, body = split_request(b"GET / HTTP/1.1\r\n\r\n")
        assert body == b""


class TestParseRequestHead:
    def test_get_simple(self):
        r = parse_request_head(b"GET /api/estado HTTP/1.1\r\nHost: 192.168.4.1")
        assert r["method"] == "GET"
        assert r["path"] == "/api/estado"
        assert r["query"] == ""
        assert r["headers"]["host"] == "192.168.4.1"

    def test_query_se_separa(self):
        r = parse_request_head(b"GET /?demo=1 HTTP/1.1")
        assert r["path"] == "/"
        assert r["query"] == "demo=1"

    def test_encabezados_en_minuscula(self):
        r = parse_request_head(b"POST /api/cmd HTTP/1.1\r\nContent-Length: 4\r\nContent-Type: text/plain")
        assert r["headers"]["content-length"] == "4"
        assert r["headers"]["content-type"] == "text/plain"

    def test_metodo_en_mayuscula(self):
        assert parse_request_head(b"get / HTTP/1.1")["method"] == "GET"

    def test_mal_formadas(self):
        assert parse_request_head(b"") is None
        assert parse_request_head(b"GET /") is None
        assert parse_request_head(b"GET / FTP/1.0") is None
        assert parse_request_head(b"GET sin-barra HTTP/1.1") is None
        assert parse_request_head(b"\xff\xfe / HTTP/1.1") is None

    def test_linea_de_encabezado_sin_dos_puntos_se_ignora(self):
        r = parse_request_head(b"GET / HTTP/1.1\r\nbasura\r\nHost: x")
        assert r["headers"] == {"host": "x"}


class TestContentLength:
    def test_sin_encabezado_es_cero(self):
        assert content_length({}) == 0

    def test_valor(self):
        assert content_length({"content-length": "7"}) == 7

    def test_invalido(self):
        assert content_length({"content-length": "abc"}) is None
        assert content_length({"content-length": "-3"}) is None
        assert content_length({"content-length": ""}) is None


class TestBuildHead:
    def test_respuesta_json(self):
        h = build_head(200, "application/json", 15)
        assert h.startswith(b"HTTP/1.1 200 OK\r\n")
        assert b"Content-Type: application/json\r\n" in h
        assert b"Content-Length: 15\r\n" in h
        assert b"Connection: close\r\n" in h
        assert b"Cache-Control: no-store\r\n" in h
        assert h.endswith(b"\r\n\r\n")

    def test_sin_cuerpo(self):
        h = build_head(204)
        assert h.startswith(b"HTTP/1.1 204 No Content\r\n")
        assert b"Content-Length" not in h


class TestCleanCommand:
    def test_quita_espacios(self):
        assert clean_command(b"  MEASURE \n") == "MEASURE"

    def test_vacio(self):
        assert clean_command(b"") is None
        assert clean_command(b"   ") is None

    def test_varias_lineas_se_rechazan(self):
        """Evita que la página cuele dos comandos en uno."""
        assert clean_command(b"SET ID=a\nMEASURE") is None

    def test_muy_largo(self):
        assert clean_command(b"SET ID=" + b"a" * 300) is None

    def test_no_es_texto(self):
        assert clean_command(b"\xff\xfe") is None


class TestCheckWebCommand:
    """Mismas reglas que por USB (parse_command), más la regla de 'ocupado'."""

    def test_comando_valido_en_espera(self):
        assert check_web_command(b"MEASURE", busy=False) == (True, "MEASURE")

    def test_set_id(self):
        assert check_web_command(b"SET ID=pe_11", busy=False) == (True, "SET ID=pe_11")

    def test_id_con_espacio_da_el_error_del_parser(self):
        ok, msg = check_web_command(b"SET ID=pe 11", busy=False)
        assert not ok
        assert "formato invalido" in msg

    def test_comando_desconocido(self):
        ok, msg = check_web_command(b"BAILAR", busy=False)
        assert not ok
        assert "desconocido" in msg

    def test_ocupado_solo_acepta_stop(self):
        ok, msg = check_web_command(b"MEASURE", busy=True)
        assert not ok
        assert msg == "midiendo: solo se acepta STOP"
        assert check_web_command(b"STOP", busy=True) == (True, "STOP")

    def test_vacio(self):
        ok, _msg = check_web_command(b"", busy=False)
        assert not ok

    def test_monitor_con_segundos(self):
        assert check_web_command(b"MONITOR 20", busy=False) == (True, "MONITOR 20")


class TestNextSessionName:
    def test_carpeta_vacia(self):
        assert next_session_name([]) == "sesion_001.csv"

    def test_sigue_al_mayor(self):
        assert next_session_name(["sesion_001.csv", "sesion_007.csv", "sesion_003.csv"]) == "sesion_008.csv"

    def test_ignora_otros_archivos(self):
        assert next_session_name(["notas.txt", "sesion_x.csv", "sesion_002.txt"]) == "sesion_001.csv"

    def test_mas_de_999(self):
        assert next_session_name(["sesion_999.csv"]) == "sesion_1000.csv"
