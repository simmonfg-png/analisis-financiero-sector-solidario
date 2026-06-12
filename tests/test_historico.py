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


def test_foto_cac():
    hist = pd.DataFrame([
        {"PERIODO": "2026-03", "CODIGO ENTIDAD": 1, "CUENTA": "100000", "VALOR": 90.0},
        {"PERIODO": "2026-04", "CODIGO ENTIDAD": 1, "CUENTA": "100000", "VALOR": 100.0},
        {"PERIODO": "2026-04", "CODIGO ENTIDAD": 1, "CUENTA": "140000", "VALOR": 60.0},
        {"PERIODO": "2026-04", "CODIGO ENTIDAD": 2, "CUENTA": "100000", "VALOR": 200.0},
        {"PERIODO": "2026-04", "CODIGO ENTIDAD": 2, "CUENTA": "999999", "VALOR": 1.0},
    ])
    meta = pd.DataFrame([{"CODIGO ENTIDAD": 1, "ENTIDAD": "COOP UNO", "ASOCIADOS": 10},
                         {"CODIGO ENTIDAD": 2, "ENTIDAD": "COOP DOS", "ASOCIADOS": 20}])
    foto, per = an.foto_cac(hist, meta)
    assert per == "2026-04"  # toma el último período
    assert len(foto) == 2
    f1 = foto.set_index("CODIGO ENTIDAD")
    assert f1.loc[1, "100000"] == 100.0  # abril, no marzo
    assert f1.loc[1, "140000"] == 60.0
    assert f1.loc[2, "140000"] == 0.0  # cuenta sin saldo → 0
    assert "999999" not in foto.columns  # solo cuentas principales
    assert f1.loc[2, "ASOCIADOS"] == 20  # metadato cruzado
