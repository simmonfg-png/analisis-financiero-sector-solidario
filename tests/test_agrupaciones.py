"""Tests del catálogo de agrupaciones y los indicadores a 6 dígitos."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src import agrupaciones as ag
from src import analytics as an


def _saldos():
    """Dos entidades: la 1 con cartera de consumo; la 2 sin actividad de crédito."""
    return pd.DataFrame({
        "CODIGO ENTIDAD": [1, 2],
        "100000": [10_000.0, 5_000.0],   # Activo
        "141100": [6_000.0, 0.0],        # Cartera consumo libranza (capital)
        "144105": [5_000.0, 0.0],        # Consumo libranza categoría A
        "144110": [1_000.0, 0.0],        # Consumo libranza categoría B (productiva Y en riesgo)
        "144500": [300.0, 0.0],          # Provisión individual capital consumo
        "146800": [200.0, 0.0],          # Provisión general
        "210500": [2_000.0, 0.0],        # Ahorro a la vista
        "211000": [1_100.0, 0.0],        # CDAT
        "211095": [100.0, 0.0],          # Intereses CDAT
        "310000": [1_500.0, 500.0],      # Capital social
        "311010": [500.0, 0.0],          # Aportes amortizados
        "400000": [1_000.0, 100.0],      # Ingresos
        "415000": [800.0, 0.0],          # Ingresos de cartera
        "422500": [50.0, 0.0],           # Recuperaciones
        "510000": [400.0, 80.0],         # Gastos de administración
        "600000": [150.0, 0.0],          # Costos financieros
    })


def test_calcular_dict_simple_y_compuesto():
    saldos = {"141100": 6_000.0, "211000": 1_100.0, "211095": 100.0}
    # Simple con signo negativo
    assert ag.calcular("CDAT_NETO", saldos) == 1_000.0
    # Compuesto recursivo: cartera bruta = solo la cuenta presente
    assert ag.calcular("CARTERA_BRUTA", saldos) == 6_000.0
    # Cuentas ausentes aportan 0
    assert ag.calcular("PROVISIONES_TOTAL", {}) == 0.0


def test_calcular_df_vectorizado():
    df = _saldos()
    cb = ag.calcular_df("CARTERA_BRUTA", df)
    assert cb.tolist() == [6_000.0, 0.0]
    dep = ag.calcular_df("DEPOSITOS_NETOS", df)
    assert dep.tolist() == [3_000.0, 0.0]   # 2000 + (1100-100)
    # Compuesto con componente de signo negativo
    improd_cap = ag.calcular_df("CARTERA_IMPRODUCTIVA_CAPITAL", df)
    assert improd_cap.tolist() == [0.0, 0.0]  # 6000 - (5000+1000)


def test_flatten_y_cuentas_necesarias():
    ctas = ag.flatten_cuentas("PROVISIONES_TOTAL")
    assert "146800" in ctas and "144500" in ctas
    todas = ag.cuentas_necesarias()
    assert {"100000", "141100", "415000"} <= todas


def test_indicadores_6dig():
    out = an.indicadores_6dig(_saldos())
    e1 = out.iloc[0]
    # Calidad por riesgo: riesgo B (1000) / cartera integral (6000)
    assert round(e1["CALIDAD_RIESGO"], 2) == round(1_000 / 6_000 * 100, 2)
    # Cobertura por riesgo: provisiones (300+200) / riesgo (1000)
    assert e1["COBERTURA_RIESGO"] == 50.0
    # Fondeo: depósitos netos (3000) / cartera bruta (6000)
    assert e1["FONDEO_DEP_CARTERA"] == 50.0
    # Aportes netos: (1500-500) / 6000
    assert round(e1["FONDEO_APORTES"], 2) == round(1_000 / 6_000 * 100, 2)
    # Eficiencia operativa: (400+150) / (800+50)
    assert round(e1["EFICIENCIA_OPERATIVA"], 2) == round(550 / 850 * 100, 2)
    # Margen financiero: (800-150)/800
    assert round(e1["MARGEN_FINANCIERO"], 2) == round(650 / 800 * 100, 2)
    # Mezcla: todo es consumo
    assert e1["PCT_CONSUMO"] == 100.0

    # Entidad 2 sin cartera → indicadores de cartera NaN, sin errores
    e2 = out.iloc[1]
    assert np.isnan(e2["CALIDAD_RIESGO"])
    assert np.isnan(e2["MARGEN_FINANCIERO"])


def test_agregar_indicadores_6dig_merge():
    ent = pd.DataFrame({"CODIGO ENTIDAD": [2, 1, 9], "ENTIDAD": ["B", "A", "C"]})
    out = an.agregar_indicadores_6dig(ent, _saldos())
    assert len(out) == 3
    # La entidad 9 no tiene saldos → NaN
    assert np.isnan(out.loc[out["CODIGO ENTIDAD"] == 9, "CALIDAD_RIESGO"]).all()
    # El merge respeta el orden y los valores
    a = out.loc[out["CODIGO ENTIDAD"] == 1].iloc[0]
    assert a["FONDEO_DEP_CARTERA"] == 50.0
