"""
test_session.py — Tests del estado de la sesión (página web)
=============================================================

Valida firmware/session.py en el PC: la regla de clasificación
(T_rel y umbral de 80 %), los cambios de estado, los límites de
memoria y el formato del diccionario que se envía como JSON.

Para correr:
    pytest -v tests/test_session.py

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import json

import pytest

from firmware import session
from firmware.session import Session, classify, relative_transmission


def nueva_sesion(**kw):
    """Sesión con los valores de config por defecto (umbral 0.80, 120 puntos)."""
    args = {"fw_version": "0.2.1", "threshold": 0.80, "max_points": 120}
    args.update(kw)
    return Session(**args)


class TestReglaDeClasificacion:
    """Misma regla de la campaña: PE si ΔV < 80 % de la referencia."""

    def test_t_rel(self):
        assert relative_transmission(1000.0, 2000.0) == pytest.approx(0.5)

    def test_sin_referencia(self):
        assert relative_transmission(1000.0, None) is None

    def test_referencia_no_positiva(self):
        assert relative_transmission(1000.0, 0.0) is None
        assert relative_transmission(1000.0, -5.0) is None

    def test_pe_debajo_del_umbral(self):
        assert classify(0.317, 0.80) == "pe"

    def test_limpia_encima_del_umbral(self):
        assert classify(0.993, 0.80) == "limpia"

    def test_justo_en_el_umbral_es_limpia(self):
        """En la campaña: PE detectado si ΔV < 80 %; 80 % exacto es limpia."""
        assert classify(0.80, 0.80) == "limpia"

    def test_sin_t_rel_no_hay_veredicto(self):
        assert classify(None, 0.80) is None

    def test_valores_reales_de_la_campana(self):
        """Extremos del 20-oct (referencia 2001.7): limpia más baja y PE más alto."""
        ref = 2001.7
        assert classify(relative_transmission(1875.6, ref), 0.80) == "limpia"   # 93.7 %
        assert classify(relative_transmission(1100.9, ref), 0.80) == "pe"       # 55.0 %

    def test_calidad_invalida(self):
        assert session.is_invalid_quality("SATURADO")
        assert session.is_invalid_quality("ERROR:sensor")
        assert not session.is_invalid_quality("OK")
        assert not session.is_invalid_quality("RUIDO_ALTO")


class TestEstados:
    """Ciclo espera → calentando → midiendo → espera, y monitor."""

    def test_arranca_en_espera(self):
        s = nueva_sesion()
        assert s.to_dict()["estado"] == "espera"
        assert not s.is_busy()

    def test_ciclo_de_medicion(self):
        s = nueva_sesion()
        s.start_warmup("R002", False, 180, 10)
        d = s.to_dict()
        assert d["estado"] == "calentando"
        assert d["run"] == "R002"
        assert d["t_total"] == 180
        assert d["m"] == 10
        assert s.is_busy()

        s.update_elapsed(92.37)
        assert s.to_dict()["t"] == pytest.approx(92.4)

        s.start_measure()
        assert s.to_dict()["estado"] == "midiendo"
        assert s.to_dict()["rep"] == 1
        s.set_rep(4)
        assert s.to_dict()["rep"] == 4

        s.to_idle()
        d = s.to_dict()
        assert d["estado"] == "espera"
        assert d["rep"] == 0
        assert not s.is_busy()

    def test_baseline_marcado(self):
        s = nueva_sesion()
        s.start_warmup("R001", True, 180, 10)
        assert s.to_dict()["baseline"] == 1

    def test_monitor(self):
        s = nueva_sesion()
        s.start_monitor(20)
        d = s.to_dict()
        assert d["estado"] == "monitor"
        assert d["t_total"] == 20
        assert d["run"] is None


class TestPuntosYMensajes:
    """Límites de memoria: la Pico no puede guardar todo."""

    def test_punto_y_ultimo(self):
        s = nueva_sesion()
        s.add_point(1851.04, "r", 22.43, 1873.47, 20.12)
        d = s.to_dict()
        assert d["serie"] == [[1851.0, "r"]]
        assert d["ultimo"] == {"dV": 1851.0, "mu_dark": 22.4, "mu_light": 1873.5, "sigma_light": 20.1}

    def test_punto_sin_detalle(self):
        s = nueva_sesion()
        s.add_point(400.0, "c")
        assert s.to_dict()["ultimo"]["mu_dark"] is None

    def test_maximo_de_puntos(self):
        s = nueva_sesion(max_points=5)
        for i in range(8):
            s.add_point(float(i), "m")
        serie = s.to_dict()["serie"]
        assert len(serie) == 5
        assert serie[0][0] == 3.0       # se descartan los más viejos
        assert serie[-1][0] == 7.0

    def test_maximo_de_mensajes(self):
        s = nueva_sesion(max_msgs=3)
        for i in range(5):
            s.add_msg("m{}".format(i))
        assert s.to_dict()["msgs"] == ["m2", "m3", "m4"]

    def test_maximo_de_llenados(self):
        s = nueva_sesion(max_fills=2)
        for i in range(4):
            s.add_result("R00{}".format(i), "x", 100.0, 0.1, "OK", False)
        assert [f["run"] for f in s.to_dict()["llenados"]] == ["R002", "R003"]


class TestResultados:
    """add_result: referencia, T_rel y veredicto de cada llenado."""

    def test_baseline_fija_la_referencia(self):
        s = nueva_sesion()
        f = s.add_result("R001", "ref", 2001.72, 0.21, "OK", True)
        assert s.to_dict()["ref"] == {"dV": 2001.7, "run": "R001"}
        assert f["veredicto"] == "ref"
        assert f["t_rel"] == 1.0
        assert f["baseline"] == 1

    def test_llenado_sin_referencia(self):
        s = nueva_sesion()
        f = s.add_result("R001", "pe_01", 841.5, 0.12, "OK", False)
        assert f["t_rel"] is None
        assert f["veredicto"] is None

    def test_llenado_pe_y_limpia(self):
        s = nueva_sesion()
        s.add_result("R001", "ref", 2001.7, 0.2, "OK", True)
        pe = s.add_result("R002", "pe_8", 534.0, 0.11, "OK", False)
        limpia = s.add_result("R003", "limpia_8", 1991.0, 0.37, "OK", False)
        assert pe["veredicto"] == "pe"
        assert pe["t_rel"] == pytest.approx(0.2668, abs=1e-4)
        assert limpia["veredicto"] == "limpia"
        assert limpia["t_rel"] == pytest.approx(0.9947, abs=1e-4)

    def test_nueva_baseline_reemplaza_la_referencia(self):
        s = nueva_sesion()
        s.add_result("R001", "ref", 2001.7, 0.2, "OK", True)
        s.add_result("R005", "ref", 1760.4, 0.2, "OK", True)
        assert s.to_dict()["ref"]["run"] == "R005"
        f = s.add_result("R006", "pe_1", 483.2, 0.1, "OK", False)
        assert f["t_rel"] == pytest.approx(0.2745, abs=1e-4)

    def test_saturado_no_clasifica(self):
        s = nueva_sesion()
        s.add_result("R001", "ref", 2001.7, 0.2, "OK", True)
        f = s.add_result("R002", "pe_1", 900.0, 0.2, "SATURADO", False)
        assert f["veredicto"] == "invalido"
        assert f["calidad"] == "SATURADO"

    def test_baseline_invalida_no_es_referencia(self):
        s = nueva_sesion()
        f = s.add_result("R001", "ref", 3100.0, 0.2, "SATURADO", True)
        assert f["veredicto"] == "invalido"
        assert s.to_dict()["ref"] is None

    def test_ruido_alto_si_clasifica(self):
        """RUIDO_ALTO no descarta (con PE la señal es baja y el criterio no aplica)."""
        s = nueva_sesion()
        s.add_result("R001", "ref", 2001.7, 0.2, "OK", True)
        f = s.add_result("R002", "pe_2", 74.0, 0.3, "RUIDO_ALTO", False)
        assert f["veredicto"] == "pe"


class TestFormatoJSON:
    """El diccionario debe poder enviarse como JSON con las claves del contrato."""

    CLAVES = {"fw", "id", "estado", "run", "baseline", "t", "t_total", "rep", "m",
              "ultimo", "serie", "ref", "umbral", "llenados", "msgs"}

    def test_claves_del_contrato(self):
        assert set(nueva_sesion().to_dict().keys()) == self.CLAVES

    def test_se_puede_serializar(self):
        s = nueva_sesion()
        s.set_sample_id("pe_10")
        s.start_warmup("R007", False, 180, 10)
        s.add_point(409.3, "c", 22.4, 431.7, 8.7)
        s.add_result("R001", "ref", 2001.7, 0.21, "OK", True)
        s.add_msg("INICIO R007 ID=pe_10 M=10 baseline=0")
        texto = json.dumps(s.to_dict())
        d = json.loads(texto)
        assert d["id"] == "pe_10"
        assert d["umbral"] == 0.8
        assert d["llenados"][0]["veredicto"] == "ref"
