"""
test_record.py — Tests unitarios de record.py
==============================================

Validación del ensamblaje de filas CSV, formateo de números y
generación de run_id. Se ejecutan en PC con pytest.

Para correr:
    pytest -v tests/test_record.py

Autores: Camila Pérez, Diego Rodriguez
Proyecto de Grado II — Universidad Santo Tomás — 2026-2
"""

import pytest

from firmware import record
from firmware import config


# ============================================================
# TESTS DE RunIdGenerator
# ============================================================

class TestRunIdGenerator:
    """Grupo de tests para RunIdGenerator."""

    def test_secuencia_basica(self):
        """Los primeros tres run_ids deben ser R001, R002, R003."""
        g = record.RunIdGenerator()
        assert g.next() == "R001"
        assert g.next() == "R002"
        assert g.next() == "R003"

    def test_current_sin_llamar_next(self):
        """Si nunca se llamó a next(), current() devuelve R000."""
        g = record.RunIdGenerator()
        assert g.current() == "R000"

    def test_current_despues_de_next(self):
        """current() no avanza, solo repite el último run_id."""
        g = record.RunIdGenerator()
        g.next()
        g.next()
        assert g.current() == "R002"
        assert g.current() == "R002"  # llamar dos veces no avanza

    def test_padding_a_tres_digitos(self):
        """Los run_ids del 1 al 999 llevan padding con ceros."""
        g = record.RunIdGenerator()
        for _ in range(9):
            g.next()
        assert g.current() == "R009"
        for _ in range(90):
            g.next()
        assert g.current() == "R099"

    def test_sin_padding_despues_de_r999(self):
        """A partir de R1000 ya no hay padding."""
        g = record.RunIdGenerator(start=999)
        assert g.next() == "R999"
        assert g.next() == "R1000"
        assert g.next() == "R1001"

    def test_dos_generadores_independientes(self):
        """Dos instancias no comparten estado."""
        g1 = record.RunIdGenerator()
        g2 = record.RunIdGenerator()
        g1.next()
        g1.next()
        g2.next()
        assert g1.current() == "R002"
        assert g2.current() == "R001"


# ============================================================
# TESTS DE format_number
# ============================================================

class TestFormatNumber:
    """Grupo de tests para format_number()."""

    def test_entero(self):
        assert record.format_number(42) == "42"
        assert record.format_number(0) == "0"
        assert record.format_number(-5) == "-5"

    def test_float_default_tres_decimales(self):
        assert record.format_number(3.14159) == "3.142"
        assert record.format_number(2015.7389) == "2015.739"

    def test_float_decimales_custom(self):
        assert record.format_number(3.14159, decimals=1) == "3.1"
        assert record.format_number(3.14159, decimals=5) == "3.14159"

    def test_none_es_cadena_vacia(self):
        assert record.format_number(None) == ""

    def test_string_devuelto_tal_cual(self):
        """Para campos como 'OK' o 'SUMMARY' se devuelve el string."""
        assert record.format_number("OK") == "OK"
        assert record.format_number("SUMMARY") == "SUMMARY"
        assert record.format_number("") == ""

    def test_bool_a_cero_o_uno(self):
        """is_baseline usa True/False → '1'/'0'."""
        assert record.format_number(True) == "1"
        assert record.format_number(False) == "0"

    def test_infinito(self):
        assert record.format_number(float("inf")) == "inf"
        assert record.format_number(float("-inf")) == "-inf"

    def test_nan(self):
        assert record.format_number(float("nan")) == "NaN"


# ============================================================
# TESTS DE build_csv_row
# ============================================================

class TestBuildCsvRow:
    """Grupo de tests para build_csv_row()."""

    def test_numero_de_campos_coincide_con_columnas(self):
        """La fila debe tener exactamente tantos campos como columnas definidas."""
        data = {col: "x" for col in config.CSV_COLUMNS}
        row = record.build_csv_row(data)
        n_campos = len(row.split(","))
        assert n_campos == len(config.CSV_COLUMNS)

    def test_orden_respeta_csv_columns(self):
        """Los valores deben aparecer en el orden exacto de CSV_COLUMNS."""
        data = {col: "pos{}".format(i) for i, col in enumerate(config.CSV_COLUMNS)}
        row = record.build_csv_row(data)
        valores = row.split(",")
        for i, valor in enumerate(valores):
            assert valor == "pos{}".format(i)

    def test_campos_faltantes_quedan_vacios(self):
        """Si una columna no está en el dict, se emite como string vacío."""
        data = {"timestamp_ms": 123, "run_id": "R001"}
        row = record.build_csv_row(data)
        campos = row.split(",")
        # El resto deben ser vacíos
        assert campos[0] == "123"
        assert campos[1] == "R001"
        for i in range(2, len(campos)):
            assert campos[i] == ""

    def test_sin_saltos_de_linea(self):
        """La fila no debe traer \\n (eso lo añade quien la emite)."""
        data = {col: "x" for col in config.CSV_COLUMNS}
        row = record.build_csv_row(data)
        assert "\n" not in row
        assert "\r" not in row


# ============================================================
# TESTS DE row_for_repetition
# ============================================================

class TestRowForRepetition:
    """Grupo de tests para row_for_repetition()."""

    def _bloques_tipicos(self):
        """Helper: crea dos bloques con datos realistas."""
        block_light = {"n": 1000, "mu": 2015.7, "sigma": 18.4,
                       "n_sat": 0, "min_val": 1950, "max_val": 2080}
        block_dark = {"n": 1000, "mu": 850.3, "sigma": 12.1,
                      "n_sat": 0, "min_val": 820, "max_val": 880}
        dv_result = {"dV": 1165.4, "sigma_dV": 22.1}
        return block_light, block_dark, dv_result

    def test_fila_tiene_numero_correcto_de_campos(self):
        light, dark, dv = self._bloques_tipicos()
        row = record.row_for_repetition(
            timestamp_ms=12345,
            run_id="R001",
            muestra_id="agua_pura_01",
            rep=1,
            block_light=light,
            block_dark=dark,
            dv_result=dv,
            quality=config.QUALITY_OK,
            is_baseline=False,
        )
        assert len(row.split(",")) == len(config.CSV_COLUMNS)

    def test_valores_clave_presentes(self):
        """Verifica que los valores dados aparezcan en la fila."""
        light, dark, dv = self._bloques_tipicos()
        row = record.row_for_repetition(
            timestamp_ms=12345, run_id="R001", muestra_id="agua_pura_01",
            rep=1, block_light=light, block_dark=dark, dv_result=dv,
            quality=config.QUALITY_OK, is_baseline=False,
        )
        assert "12345" in row
        assert "R001" in row
        assert "agua_pura_01" in row
        assert "OK" in row
        assert config.FW_VERSION in row

    def test_is_baseline_true(self):
        """is_baseline=True debe aparecer como '1' al final."""
        light, dark, dv = self._bloques_tipicos()
        row = record.row_for_repetition(
            timestamp_ms=1, run_id="R001", muestra_id="X",
            rep=1, block_light=light, block_dark=dark, dv_result=dv,
            quality=config.QUALITY_OK, is_baseline=True,
        )
        campos = row.split(",")
        # 'is_baseline' es la última columna
        assert campos[-1] == "1"


# ============================================================
# TESTS DE row_for_summary
# ============================================================

class TestRowForSummary:
    """Grupo de tests para row_for_summary()."""

    def test_rep_es_summary(self):
        """La columna 'rep' debe decir exactamente 'SUMMARY'."""
        dv_summary = {"n_reps": 10, "mean_dV": 1165.5,
                      "sigma_dV": 0.8, "min_dV": 1164.0, "max_dV": 1167.0}
        row = record.row_for_summary(
            timestamp_ms=99999, run_id="R001", muestra_id="agua_pura_01",
            N=1000, dv_summary=dv_summary,
            quality=config.QUALITY_OK, is_baseline=False,
        )
        campos = row.split(",")
        # El índice de 'rep' según CSV_COLUMNS
        idx_rep = config.CSV_COLUMNS.index("rep")
        assert campos[idx_rep] == "SUMMARY"

    def test_campos_de_bloque_vacios(self):
        """mu_dark, sigma_dark, mu_light, sigma_light, n_sat_* van vacíos
        en la fila SUMMARY porque son valores agregados."""
        dv_summary = {"n_reps": 10, "mean_dV": 1165.5, "sigma_dV": 0.8,
                      "min_dV": 1164.0, "max_dV": 1167.0}
        row = record.row_for_summary(
            timestamp_ms=99999, run_id="R001", muestra_id="X",
            N=1000, dv_summary=dv_summary,
            quality=config.QUALITY_OK,
        )
        campos = row.split(",")
        for col_name in ["mu_dark", "sigma_dark", "mu_light",
                         "sigma_light", "n_sat_light", "n_sat_dark"]:
            idx = config.CSV_COLUMNS.index(col_name)
            assert campos[idx] == "", \
                "Esperaba '{}' vacío, encontré: '{}'".format(col_name, campos[idx])