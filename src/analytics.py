"""
analytics.py — Cálculos sobre el DataFrame de entidades (nivel sector/entidad).

A diferencia de indicators.py (lógica pura para un balance suelto), aquí se
trabaja de forma vectorizada sobre todas las entidades a la vez.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import agrupaciones as ag

# Códigos de cuentas principales usados en los indicadores
A = "100000"   # Activo
P = "200000"   # Pasivo
PAT = "300000"  # Patrimonio
CART = "140000"  # Cartera de créditos
DEP = "210000"  # Depósitos
APO = "310000"  # Capital social (aportes)
EXC = "350000"  # Excedente / pérdida del ejercicio
ING = "400000"  # Ingresos
GTO = "500000"  # Gastos
GADM = "510000"  # Gastos de administración


def _ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    """num/den*100 protegido contra división por cero."""
    return np.where(den != 0, num / den * 100, np.nan)


def agregar_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una copia de df con columnas de indicadores financieros (%)."""
    d = df.copy()
    d["ROA"] = _ratio(d[EXC], d[A])
    d["SOLVENCIA"] = _ratio(d[PAT], d[A])
    d["ENDEUDAMIENTO"] = _ratio(d[P], d[A])
    d["CARTERA_ACTIVO"] = _ratio(d[CART], d[A])
    d["FONDEO_DEPOSITOS"] = _ratio(d[DEP], d[A])
    d["MARGEN_EXCEDENTE"] = _ratio(d[EXC], d[ING])
    d["EFICIENCIA"] = _ratio(d[GADM], d[ING])
    d["ROE"] = _ratio(d[EXC], d[PAT])
    return d


def indicadores_6dig(saldos: pd.DataFrame) -> pd.DataFrame:
    """
    Indicadores calculados con el catálogo de agrupaciones (cuentas a 6 dígitos),
    portados del proyecto analisis_tasas. Recibe el DataFrame ancho de
    saldos_6dig.parquet (una fila por entidad, una columna por código PUC) y
    devuelve CODIGO ENTIDAD + columnas de indicadores (en %).
    """
    def A(alias: str) -> pd.Series:
        return ag.calcular_df(alias, saldos)

    cb    = A("CARTERA_BRUTA")
    ci    = A("CARTERA_INTEGRAL")
    ri    = A("CARTERA_EN_RIESGO")
    act   = A("ACTIVOS")
    ing   = A("INGRESOS_TOTAL")
    inti  = A("INGRESOS_CARTERA")
    recup = A("RECUPERACIONES")
    gadm  = A("GASTOS_ADMINISTRACION")
    cfin  = A("COSTOS_FINANCIEROS")
    csoc  = A("CAPITAL_SOCIAL")
    ef_den = inti + recup

    out = pd.DataFrame({"CODIGO ENTIDAD": saldos["CODIGO ENTIDAD"].astype(int)})

    # Calidad y cobertura de cartera
    out["CALIDAD_RIESGO"]    = _ratio(ri, ci)
    out["COBERTURA_RIESGO"]  = _ratio(A("PROVISIONES_TOTAL"), ri)
    out["COBERTURA_GENERAL"] = _ratio(
        A("PROVISIONES_INDIVIDUALES_CAPITAL") + A("PROVISIONES_GENERALES"), cb)
    out["CARTERA_PRODUCTIVA"] = _ratio(A("CARTERA_PRODUCTIVA_AB"), cb)

    # Mezcla de cartera por modalidad
    out["PCT_VIVIENDA"]   = _ratio(A("CARTERA_BRUTA_VIVIENDA"), cb)
    out["PCT_CONSUMO"]    = _ratio(A("CARTERA_BRUTA_CONSUMO_LIBRANZA")
                                   + A("CARTERA_BRUTA_CONSUMO_CAJA"), cb)
    out["PCT_MICROCREDITO"] = _ratio(A("CARTERA_BRUTA_MICROCREDITO"), cb)
    out["PCT_COMERCIAL"]  = _ratio(A("CARTERA_BRUTA_COMERCIAL"), cb)
    out["PCT_PRODUCTIVO"] = _ratio(A("CARTERA_BRUTA_PRODUCTIVO")
                                   + A("CARTERA_BRUTA_EMPLEADOS"), cb)

    # Fondeo y estructura
    out["FONDEO_DEP_CARTERA"] = _ratio(A("DEPOSITOS_NETOS"), cb)
    out["FONDEO_APORTES"]     = _ratio(A("APORTES_SOCIALES_ASOCIADOS"), cb)
    out["DEUDA_ACTIVOS"]      = _ratio(A("OBLIGACIONES_FINANCIERAS"), act)
    out["ACTIVOS_IMPRODUCTIVOS"] = _ratio(A("ACTIVO_IMPRODUCTIVO"), act)

    # Capital
    out["CAPITAL_INSTITUCIONAL"] = _ratio(A("CAPITAL_INSTITUCIONAL"), act)
    out["IRREDUCIBLE_SOCIAL"]    = _ratio(A("CAPITAL_IRREDUCIBLE"), csoc)

    # Eficiencia y márgenes (estado de resultados)
    out["EFICIENCIA_OPERATIVA"] = _ratio(gadm + cfin, ef_den)
    out["MARGEN_FINANCIERO"]    = _ratio(inti - cfin, inti)
    out["MARGEN_OPERACIONAL"]   = _ratio(inti + recup - cfin - gadm, inti)
    out["DIVERSIFICACION"]      = _ratio(ing - inti - recup, ing)
    out["DEPENDENCIA_MARGEN"]   = _ratio(ef_den, ing)

    return out


def agregar_indicadores_6dig(df: pd.DataFrame, saldos: pd.DataFrame) -> pd.DataFrame:
    """Cruza el DataFrame de entidades con los indicadores a 6 dígitos."""
    return df.merge(indicadores_6dig(saldos), on="CODIGO ENTIDAD", how="left")


def resumen_sector(df: pd.DataFrame) -> dict:
    """Cifras agregadas del conjunto de entidades recibido."""
    return {
        "entidades": int(len(df)),
        "activo": float(df[A].sum()),
        "pasivo": float(df[P].sum()),
        "patrimonio": float(df[PAT].sum()),
        "cartera": float(df[CART].sum()),
        "depositos": float(df[DEP].sum()),
        "excedente": float(df[EXC].sum()),
        "ingresos": float(df[ING].sum()),
        "asociados": int(df["ASOCIADOS"].sum()),
        "empleados": int(df["EMPLEADOS"].sum()),
    }


def por_grupo(df: pd.DataFrame, col: str, top: int | None = None) -> pd.DataFrame:
    """Agrega activo, entidades y asociados por una columna categórica."""
    g = (df.groupby(col)
         .agg(activo=(A, "sum"), entidades=(A, "size"), asociados=("ASOCIADOS", "sum"))
         .reset_index()
         .sort_values("activo", ascending=False))
    if top:
        g = g.head(top)
    return g.reset_index(drop=True)


def ranking(df: pd.DataFrame, col: str, n: int = 15, ascendente: bool = False) -> pd.DataFrame:
    cols = ["ENTIDAD", "SIGLA", "TIPO ENTIDAD", "DEPARTAMENTO", col]
    cols = [c for c in cols if c in df.columns]
    return (df.sort_values(col, ascending=ascendente)
            .head(n)[cols]
            .reset_index(drop=True))


# ── Histórico mensual CAC ─────────────────────────────────────────────────────

def serie_historica(hist: pd.DataFrame, cuentas: list[str],
                    codigo: int | None = None) -> pd.DataFrame:
    """
    Serie mensual (PERIODO × CUENTA) a partir del histórico largo.
    Si `codigo` es None agrega todo el sector; si no, filtra esa entidad.
    """
    d = hist if codigo is None else hist[hist["CODIGO ENTIDAD"] == codigo]
    d = d[d["CUENTA"].isin(cuentas)]
    piv = d.pivot_table(index="PERIODO", columns="CUENTA", values="VALOR",
                        aggfunc="sum", observed=True)
    piv.columns = piv.columns.astype(str)
    piv.index = piv.index.astype(str)  # PERIODO llega como categórico sin orden
    return piv.sort_index()


def entidades_por_periodo(hist: pd.DataFrame) -> pd.Series:
    """Número de entidades que reportan en cada período."""
    n = hist.groupby("PERIODO", observed=True)["CODIGO ENTIDAD"].nunique()
    n.index = n.index.astype(str)
    return n.sort_index()


def variacion_anual(serie: pd.Series) -> float:
    """Variación % del último dato frente a 12 meses atrás (NaN si no alcanza)."""
    if len(serie) < 13 or serie.iloc[-13] == 0:
        return float("nan")
    return float((serie.iloc[-1] / serie.iloc[-13] - 1) * 100)


CUENTAS_FOTO = [A, P, PAT, CART, DEP, EXC]


def foto_cac(hist: pd.DataFrame, meta: pd.DataFrame,
             periodo: str | None = None) -> tuple[pd.DataFrame, str]:
    """
    Foto del sector CAC en un período del histórico (por defecto el último):
    una fila por entidad con las cuentas principales en columnas, enriquecida
    con los metadatos de `meta` (nombre, sigla, departamento, asociados…).
    Devuelve (DataFrame, período usado).
    """
    per = periodo or str(hist["PERIODO"].astype(str).max())
    d = hist[(hist["PERIODO"].astype(str) == per) & hist["CUENTA"].isin(CUENTAS_FOTO)]
    w = (d.pivot_table(index="CODIGO ENTIDAD", columns="CUENTA", values="VALOR",
                       aggfunc="sum", observed=True)
         .reindex(columns=CUENTAS_FOTO).fillna(0.0))
    w.columns = [str(c) for c in w.columns]
    return w.reset_index().merge(meta, on="CODIGO ENTIDAD", how="left"), per
