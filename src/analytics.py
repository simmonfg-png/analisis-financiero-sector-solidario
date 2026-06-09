"""
analytics.py — Cálculos sobre el DataFrame de entidades (nivel sector/entidad).

A diferencia de indicators.py (lógica pura para un balance suelto), aquí se
trabaja de forma vectorizada sobre todas las entidades a la vez.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

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
