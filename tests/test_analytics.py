"""Tests de la analítica a nivel sector/entidad (src/analytics.py)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src import analytics as an


def _df():
    return pd.DataFrame({
        "ENTIDAD": ["A", "B"],
        "SIGLA": ["A", "B"],
        "TIPO ENTIDAD": ["X", "X"],
        "DEPARTAMENTO": ["D1", "D2"],
        "ASOCIADOS": [100, 300],
        "EMPLEADOS": [5, 8],
        "100000": [10_000.0, 20_000.0],   # Activo
        "200000": [7_000.0, 12_000.0],    # Pasivo
        "300000": [3_000.0, 8_000.0],     # Patrimonio
        "140000": [6_000.0, 5_000.0],     # Cartera
        "210000": [5_000.0, 9_000.0],     # Depósitos
        "310000": [1_000.0, 2_000.0],     # Aportes
        "350000": [200.0, 0.0],           # Excedente
        "400000": [1_000.0, 0.0],         # Ingresos
        "500000": [800.0, 0.0],           # Gastos
        "510000": [500.0, 0.0],           # Gastos admón.
    })


def test_indicadores_basicos():
    d = an.agregar_indicadores(_df())
    fila = d.iloc[0]
    assert fila["ROA"] == 2.0
    assert fila["SOLVENCIA"] == 30.0
    assert fila["ENDEUDAMIENTO"] == 70.0
    assert fila["CARTERA_ACTIVO"] == 60.0
    assert round(fila["MARGEN_EXCEDENTE"], 1) == 20.0


def test_division_por_cero_devuelve_nan():
    d = an.agregar_indicadores(_df())
    # Entidad B no tiene ingresos → margen/eficiencia = NaN, no error
    assert np.isnan(d.iloc[1]["MARGEN_EXCEDENTE"])
    assert np.isnan(d.iloc[1]["EFICIENCIA"])


def test_resumen_sector():
    r = an.resumen_sector(_df())
    assert r["entidades"] == 2
    assert r["activo"] == 30_000.0
    assert r["asociados"] == 400


def test_por_grupo_y_ranking():
    df = _df()
    g = an.por_grupo(df, "TIPO ENTIDAD")
    assert g.iloc[0]["activo"] == 30_000.0
    assert g.iloc[0]["entidades"] == 2
    top = an.ranking(df, "100000", n=1)
    assert top.iloc[0]["SIGLA"] == "B"   # mayor activo
