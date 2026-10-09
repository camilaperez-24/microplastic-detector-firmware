"""
test_stats.py — Tests unitarios de stats.py
============================================

Validación de las funciones del módulo firmware.stats
usando pytest. Estos tests se ejecutan en PC (CPython),
NO en la Pico. Verifican que la matemática del firmware
sea correcta antes de ponerla en hardware.

Para correr todos los tests:
    pytest -v

Para correr solo este archivo:
    pytest -v tests/test_stats.py

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import math
import random

import pytest

from firmware import stats
from firmware import config


# ============================================================
# TESTS DE welford_block()
# ============================================================

class TestWelfordBlock:
    """Grupo de tests para la función welford_block()."""

    def test_caso_tipico(self):
        """Muestras [1,2,3,4,5]: media conocida = 3.0, sigma_muestral conocida ≈ 1.5811."""
        result = stats.welford_block([1, 2, 3, 4, 5])
        assert result["n"] == 5
        assert result["mu"] == pytest.approx(3.0)
        assert result["sigma"] == pytest.approx(1.5811388, abs=1e-5)
        assert result["n_sat"] == 0
        assert result["min_val"] == 1
        assert result["max_val"] == 5

    def test_lista_vacia(self):
        """Lista vacía: todos los campos en cero, sin error."""
        result = stats.welford_block([])
        assert result["n"] == 0
        assert result["mu"] == 0.0
        assert result["sigma"] == 0.0
        assert result["n_sat"] == 0

    def test_un_solo_elemento(self):
        """Un solo valor: media = ese valor, sigma = 0 por convención."""
        result = stats.welford_block([42])
        assert result["n"] == 1
        assert result["mu"] == pytest.approx(42.0)
        assert result["sigma"] == 0.0
        assert result["min_val"] == 42
        assert result["max_val"] == 42

    def test_todos_iguales(self):
        """Muestras todas iguales: sigma debe ser exactamente 0."""
        result = stats.welford_block([100] * 20)
        assert result["mu"] == pytest.approx(100.0)
        assert result["sigma"] == 0.0

    def test_welford_vs_formula_clasica(self):
        """Compara el resultado de Welford con la fórmula clásica
        en un dataset moderado, donde ambas deben coincidir."""
        data = [i for i in range(1, 101)]  # 1..100
        n = len(data)
        mean_classic = sum(data) / n
        variance_classic = sum((x - mean_classic) ** 2 for x in data) / (n - 1)
        sigma_classic = math.sqrt(variance_classic)

        result = stats.welford_block(data)
        assert result["mu"] == pytest.approx(mean_classic, abs=1e-9)
        assert result["sigma"] == pytest.approx(sigma_classic, abs=1e-9)

    def test_adc_realista(self):
        """Simulación realista: 1000 muestras gaussianas con
        mu=2000 y sigma=50. Welford debe recuperar ambos con
        error pequeño."""
        random.seed(42)  # reproducibilidad
        mu_true = 2000
        sigma_true = 50
        data = [random.gauss(mu_true, sigma_true) for _ in range(1000)]

        result = stats.welford_block(data)
        # Toleramos ~5% de error estadístico por tamaño de muestra
        assert result["mu"] == pytest.approx(mu_true, abs=5)
        assert result["sigma"] == pytest.approx(sigma_true, abs=5)

    def test_conteo_saturaciones(self):
        """Verifica que n_sat cuenta correctamente muestras
        iguales o superiores a ADC_SATURATION_VALUE (4095)."""
        data = [100, 200, 4095, 4095, 4096, 300, 4095]
        # Hay 4 muestras >= 4095
        result = stats.welford_block(data)
        assert result["n_sat"] == 4

    def test_estabilidad_numerica_valores_grandes(self):
        """Dataset con valores grandes y variación pequeña — el caso
        exacto donde la fórmula clásica Σx² − (Σx)²/n falla por
        cancelación catastrófica. Welford debe dar sigma correcta."""
        base = 10_000_000
        data = [base + i for i in range(1, 101)]  # 10000001..10000100
        # La sigma teórica es la misma que para [1..100]
        sigma_esperada = math.sqrt(
            sum((i - 50.5) ** 2 for i in range(1, 101)) / 99
        )
        result = stats.welford_block(data)
        assert result["sigma"] == pytest.approx(sigma_esperada, abs=1e-6)


# ============================================================
# TESTS DE delta_v()
# ============================================================

class TestDeltaV:
    """Grupo de tests para delta_v()."""

    def test_caso_tipico(self):
        """mu_light=2.0, mu_dark=0.5 → dV=1.5. Propagación por suma en cuadratura."""
        result = stats.delta_v(mu_light=2.0, sigma_light=0.1,
                               mu_dark=0.5, sigma_dark=0.05)
        assert result["dV"] == pytest.approx(1.5)
        esperado_sigma = math.sqrt(0.1 ** 2 + 0.05 ** 2)
        assert result["sigma_dV"] == pytest.approx(esperado_sigma)

    def test_dark_mayor_que_light(self):
        """Si por alguna razón dark > light, dV debe salir negativo (no abs)."""
        result = stats.delta_v(mu_light=1.0, sigma_light=0.1,
                               mu_dark=2.0, sigma_dark=0.1)
        assert result["dV"] == pytest.approx(-1.0)

    def test_sigmas_cero(self):
        """Si ambas sigmas son cero, sigma_dV también debe ser cero."""
        result = stats.delta_v(mu_light=5.0, sigma_light=0.0,
                               mu_dark=1.0, sigma_dark=0.0)
        assert result["sigma_dV"] == 0.0


# ============================================================
# TESTS DE snr()
# ============================================================

class TestSnr:
    """Grupo de tests para snr()."""

    def test_caso_tipico(self):
        """mu=10, sigma=2 → SNR=5."""
        assert stats.snr(10.0, 2.0) == pytest.approx(5.0)

    def test_mu_negativo(self):
        """SNR usa |mu|, por lo que mu negativo debe dar SNR positivo."""
        assert stats.snr(-10.0, 2.0) == pytest.approx(5.0)

    def test_sigma_cero(self):
        """sigma=0 → SNR infinito."""
        assert stats.snr(5.0, 0.0) == float("inf")


# ============================================================
# TESTS DE quality_flag()
# ============================================================

class TestQualityFlag:
    """Grupo de tests para quality_flag()."""

    def _bloque_ok(self):
        """Helper: bloque con buena calidad."""
        return {"n": 1000, "mu": 2000.0, "sigma": 20.0, "n_sat": 0,
                "min_val": 1950, "max_val": 2050}

    def test_todo_bien(self):
        """Dos bloques sanos → OK."""
        result = stats.quality_flag(self._bloque_ok(), self._bloque_ok())
        assert result == config.QUALITY_OK

    def test_saturacion_light(self):
        """Más de 1% de muestras saturadas en LIGHT → SATURADO."""
        light = self._bloque_ok()
        light["n_sat"] = 50  # 5% saturado
        result = stats.quality_flag(light, self._bloque_ok())
        assert result == config.QUALITY_SATURATED

    def test_saturacion_dark(self):
        """Más de 1% saturado en DARK también → SATURADO."""
        dark = self._bloque_ok()
        dark["n_sat"] = 50
        result = stats.quality_flag(self._bloque_ok(), dark)
        assert result == config.QUALITY_SATURATED

    def test_ruido_alto(self):
        """CV = sigma/mu > 5% → RUIDO_ALTO."""
        light = self._bloque_ok()
        light["sigma"] = 200.0  # CV = 10%
        result = stats.quality_flag(light, self._bloque_ok())
        assert result == config.QUALITY_HIGH_NOISE

    def test_prioridad_saturacion_sobre_ruido(self):
        """Si hay saturación Y ruido alto, prevalece SATURADO."""
        light = self._bloque_ok()
        light["n_sat"] = 50
        light["sigma"] = 500.0  # también ruidoso
        result = stats.quality_flag(light, self._bloque_ok())
        assert result == config.QUALITY_SATURATED


# ============================================================
# TESTS DE summarize_repetitions()
# ============================================================

class TestSummarizeRepetitions:
    """Grupo de tests para summarize_repetitions()."""

    def test_caso_tipico(self):
        """10 repeticiones con ΔV conocidos."""
        dvs = [1.0, 1.1, 0.9, 1.05, 0.95, 1.02, 0.98, 1.03, 0.97, 1.0]
        result = stats.summarize_repetitions(dvs)
        assert result["n_reps"] == 10
        assert result["mean_dV"] == pytest.approx(sum(dvs) / len(dvs))
        assert result["min_dV"] == 0.9
        assert result["max_dV"] == 1.1

    def test_lista_vacia(self):
        """Lista vacía: n_reps = 0, no debe fallar."""
        result = stats.summarize_repetitions([])
        assert result["n_reps"] == 0