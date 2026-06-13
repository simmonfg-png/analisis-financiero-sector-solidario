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


def _panel_hist():
    """Histórico de juguete con cuentas de agrupaciones (2 entidades, 2 meses)."""
    filas = []
    datos = {  # cuenta -> (ent1, ent2)
        "210500": (100.0, 50.0),   # AHORRO_VISTA
        "211000": (80.0, 20.0),    # CDAT bruto
        "211095": (5.0, 0.0),      # intereses CDAT (se restan en CDAT_NETO)
        "100000": (1000.0, 500.0), # ACTIVOS
        "300000": (300.0, 200.0),  # PATRIMONIO
        "350000": (60.0, 30.0),    # EXCEDENTE
    }
    for per in ["2026-03", "2026-06"]:
        for cta, (v1, v2) in datos.items():
            filas.append({"PERIODO": per, "CODIGO ENTIDAD": 1, "CUENTA": cta, "VALOR": v1})
            filas.append({"PERIODO": per, "CODIGO ENTIDAD": 2, "CUENTA": cta, "VALOR": v2})
    return pd.DataFrame(filas)


def test_panel_mensual_y_serie_alias():
    panel = an.panel_mensual(_panel_hist())
    assert list(panel.index) == ["2026-03", "2026-06"]
    # AHORRO_VISTA (210500) = suma de las 2 entidades = 150
    av = an.serie_alias(panel, "AHORRO_VISTA")
    assert av.loc["2026-03"] == 150.0
    # CDAT_NETO = 211000 - 211095 = (80+20) - (5+0) = 95
    assert an.serie_alias(panel, "CDAT_NETO").loc["2026-06"] == 95.0


def test_valor_y_ratio_alias():
    panel = an.panel_mensual(_panel_hist())
    assert an.valor_alias(panel, "2026-03", "AHORRO_VISTA") == 150.0
    assert math.isnan(an.valor_alias(panel, "2099-01", "AHORRO_VISTA"))
    # DEPOSITOS_NETOS / ACTIVOS: (150 + 95 + 0) / 1500 * 100
    r = an.ratio_alias(panel, "DEPOSITOS_NETOS", "ACTIVOS")
    assert math.isclose(r.loc["2026-03"], 245.0 / 1500 * 100)


def test_roa_roe_anualizado():
    panel = an.panel_mensual(_panel_hist())
    roa, roe = an.roa_roe(panel)
    # marzo (mes 3): ROA = 90/1500 *100 * 12/3 ; ROE = 90/500 *100 * 12/3
    assert math.isclose(roa.loc["2026-03"], 90 / 1500 * 100 * 4)
    assert math.isclose(roe.loc["2026-03"], 90 / 500 * 100 * 4)
    # junio (mes 6): factor 12/6 = 2
    assert math.isclose(roa.loc["2026-06"], 90 / 1500 * 100 * 2)


def test_panel_sin_nan_en_cuentas_ausentes():
    # entidad 1 reporta una cuenta extra en un solo período; el panel debe
    # quedar con 0.0 (no NaN) en el período donde no aparece, para que las
    # agrupaciones escalares no se contaminen.
    base = _panel_hist()
    extra = pd.DataFrame([{"PERIODO": "2026-03", "CODIGO ENTIDAD": 1,
                           "CUENTA": "146800", "VALOR": 7.0}])  # PROVISIONES_GENERALES
    panel = an.panel_mensual(pd.concat([base, extra], ignore_index=True))
    assert panel.loc["2026-06", "146800"] == 0.0  # ausente ese mes → 0, no NaN
    # valor_alias escalar no devuelve NaN por la cuenta ausente
    assert an.valor_alias(panel, "2026-06", "PROVISIONES_GENERALES") == 0.0
    assert an.valor_alias(panel, "2026-03", "PROVISIONES_GENERALES") == 7.0


def test_categoria_cac():
    uvr = an.UVR_DIC_2024
    t1 = 315_000_000 * uvr        # 118.684.534.500
    t2 = 1_400_000_000 * uvr      # 527.486.820.000
    assert an.categoria_cac(t1 - 1) == "Básica"
    assert an.categoria_cac(t1) == "Básica"        # igual o inferior → Básica
    assert an.categoria_cac(t1 + 1) == "Intermedia"
    assert an.categoria_cac(t2 - 1) == "Intermedia"
    assert an.categoria_cac(t2) == "Plena"         # igual o superior → Plena
    s = an.categoria_cac(pd.Series([1e9, 2e11, 6e11]))
    assert list(s) == ["Básica", "Intermedia", "Plena"]


def test_subcategoria_cac():
    uvr = an.UVR_DIC_2024
    t1 = 315_000_000 * uvr
    t2 = 1_400_000_000 * uvr
    mid = (t1 + t2) / 2
    b1, b2 = t1 / 3, 2 * t1 / 3
    assert an.subcategoria_cac(t2) == "Plena"
    assert an.subcategoria_cac(mid) == "Intermedia - Grupo 1"
    assert an.subcategoria_cac(mid - 1) == "Intermedia - Grupo 2"
    assert an.subcategoria_cac(t1) == "Básica - Grupo 1"      # tope de Básica
    assert an.subcategoria_cac(b2) == "Básica - Grupo 1"
    assert an.subcategoria_cac(b2 - 1) == "Básica - Grupo 2"
    assert an.subcategoria_cac(b1) == "Básica - Grupo 2"
    assert an.subcategoria_cac(b1 - 1) == "Básica - Grupo 3"
    s = an.subcategoria_cac(pd.Series([10e9, 100e9, 200e9, 400e9, 1e12]))
    assert list(s) == ["Básica - Grupo 3", "Básica - Grupo 1",
                       "Intermedia - Grupo 2", "Intermedia - Grupo 1", "Plena"]


def test_clasificar_cac_fija_por_periodo_referencia():
    uvr = an.UVR_DIC_2024
    t2 = 1_400_000_000 * uvr
    # ent 1: Básica en dic-2024, crece a Plena en 2026 → debe quedar por dic-2024
    # ent 2: entra después (solo 2026) → usa su primer período disponible
    filas = [
        {"PERIODO": "2024-12", "CODIGO ENTIDAD": 1, "CUENTA": "100000", "VALOR": 10e9},
        {"PERIODO": "2026-04", "CODIGO ENTIDAD": 1, "CUENTA": "100000", "VALOR": t2 + 1},
        {"PERIODO": "2026-04", "CODIGO ENTIDAD": 2, "CUENTA": "100000", "VALOR": t2 + 1},
    ]
    cl = an.clasificar_cac(pd.DataFrame(filas), ref_periodo="2024-12").set_index("CODIGO ENTIDAD")
    assert cl.loc[1, "CATEGORIA"] == "Básica"   # por dic-2024, no por 2026
    assert cl.loc[2, "CATEGORIA"] == "Plena"    # sin dic-2024 → primer período


def test_clasificar_cac_overrides():
    filas = [
        {"PERIODO": "2024-12", "CODIGO ENTIDAD": 1, "CUENTA": "100000", "VALOR": 10e9},
        {"PERIODO": "2024-12", "CODIGO ENTIDAD": 2, "CUENTA": "100000", "VALOR": 10e9},
    ]
    cl = an.clasificar_cac(pd.DataFrame(filas), ref_periodo="2024-12",
                           overrides={2: "Intermedia"}).set_index("CODIGO ENTIDAD")
    assert cl.loc[1, "CATEGORIA"] == "Básica"          # sin override
    assert cl.loc[2, "CATEGORIA"] == "Intermedia"      # forzada
    assert cl.loc[2, "SUBCATEGORIA"] == "Intermedia - Grupo 1"
