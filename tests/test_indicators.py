"""
Tests de la lógica pura de indicadores. Ejecutar:  pytest
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.indicators import (
    indice_solvencia, cartera_sobre_activo, margen_excedente, calcular_indicadores
)
from config import CUENTAS


def test_indice_solvencia():
    # Patrimonio 900 sobre activo 10.000 → 9%
    assert indice_solvencia(900, 10_000) == 9.0


def test_solvencia_activo_cero_no_explota():
    assert indice_solvencia(900, 0) == 0.0


def test_cartera_sobre_activo():
    assert cartera_sobre_activo(3_500, 10_000) == 35.0


def test_margen_excedente():
    assert round(margen_excedente(120, 1_000), 2) == 12.0


def test_calcular_indicadores_desde_balance():
    balance = {
        CUENTAS["activo"]:     10_000,
        CUENTAS["pasivo"]:      7_000,
        CUENTAS["patrimonio"]:  3_000,
        CUENTAS["cartera"]:     6_000,
        CUENTAS["depositos"]:   5_000,
        CUENTAS["excedente"]:     200,
        CUENTAS["ingresos"]:    1_000,
    }
    ind = calcular_indicadores(balance)
    assert ind["Activo"] == 10_000
    assert ind["Índice de solvencia (%)"] == 30.0
    assert ind["Cartera / Activo (%)"] == 60.0
    assert ind["ROA (%)"] == 2.0
