"""Tests de las funciones de series históricas (analytics)."""
import math

import pandas as pd

from src import analytics as an


def _hist():
    """Histórico largo de juguete: 2 entidades, 2 cuentas, 14 períodos."""
    periodos = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01", "2026-02"]
    filas = []
    for i, p in enumerate(periodos):
        filas.append({"PERIODO": p, "CODIGO ENTIDAD": 1, "CUENTA": "100000",
                      "VALOR": 100.0 + i})
        filas.append({"PERIODO": p, "CODIGO ENTIDAD": 2, "CUENTA": "100000",
                      "VALOR": 200.0})
        filas.append({"PERIODO": p, "CODIGO ENTIDAD": 1, "CUENTA": "140000",
                      "VALOR": 50.0})
    return pd.DataFrame(filas)


def test_serie_historica_sector_suma_entidades():
    s = an.serie_historica(_hist(), ["100000"])
    assert s.loc["2025-01", "100000"] == 300.0  # 100 + 200
    assert list(s.index) == sorted(s.index)


def test_serie_historica_filtra_entidad_y_cuentas():
    s = an.serie_historica(_hist(), ["100000", "140000"], codigo=1)
    assert s.loc["2025-01", "100000"] == 100.0
    assert s.loc["2026-02", "140000"] == 50.0
    assert "200000" not in s.columns


def test_entidades_por_periodo():
    n = an.entidades_por_periodo(_hist())
    assert n.loc["2025-06"] == 2
    assert len(n) == 14


def test_variacion_anual():
    s = an.serie_historica(_hist(), ["100000"], codigo=1)["100000"]
    # último (2026-02 = 113) vs 12 meses atrás (2025-02 = 101)
    assert math.isclose(an.variacion_anual(s), (113 / 101 - 1) * 100)
    # serie corta: no alcanza para 12 meses
    assert math.isnan(an.variacion_anual(s.head(5)))
