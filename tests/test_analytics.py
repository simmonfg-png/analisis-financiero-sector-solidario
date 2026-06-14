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


def test_trimestres_hasta():
    assert an.trimestres_hasta("2026-03", "2027-12") == [
        "2026-06", "2026-09", "2026-12",
        "2027-03", "2027-06", "2027-09", "2027-12"]
    # un solo paso
    assert an.trimestres_hasta("2027-09", "2027-12") == ["2027-12"]


def test_proyectar_ets():
    # Serie trimestral con tendencia + estacionalidad (8 años, positiva)
    idx = [f"{y}-{m:02d}" for y in range(2018, 2026) for m in (3, 6, 9, 12)]
    base = np.linspace(100, 200, len(idx))
    estacional = np.tile([1.0, 1.02, 1.04, 1.06], len(idx) // 4)
    serie = pd.Series(base * estacional, index=idx)
    futuros = ["2026-03", "2026-06", "2026-09", "2026-12"]
    proy = an.proyectar_ets(serie, futuros, nivel=0.8)
    assert list(proy.index) == futuros
    assert {"media", "inf", "sup"}.issubset(proy.columns)
    # la banda contiene a la media y la tendencia sigue creciendo
    assert (proy["inf"] <= proy["media"]).all()
    assert (proy["media"] <= proy["sup"]).all()
    assert proy["media"].iloc[-1] > serie.iloc[-1]


def test_proyectar_ets_serie_corta_devuelve_none():
    serie = pd.Series([1.0, 2.0, 3.0], index=["2025-06", "2025-09", "2025-12"])
    assert an.proyectar_ets(serie, ["2026-03"]) is None
