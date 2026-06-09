"""
data.py — Acceso a los datos consolidados (parquet) con caché de Streamlit.

Si los parquet no existen, ejecuta el ETL automáticamente la primera vez.
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from config import DATA_PROC


def _ruta(nombre: str) -> str:
    return os.path.join(DATA_PROC, nombre)


def _asegurar_datos() -> None:
    """Genera los parquet si aún no existen."""
    if not os.path.exists(_ruta("entidades.parquet")):
        from src.etl import main as run_etl
        run_etl()


@st.cache_data(show_spinner="Cargando datos del sector…")
def entidades() -> pd.DataFrame:
    _asegurar_datos()
    return pd.read_parquet(_ruta("entidades.parquet"))


@st.cache_data
def tasas() -> pd.DataFrame:
    _asegurar_datos()
    return pd.read_parquet(_ruta("tasas.parquet"))


@st.cache_data
def cac_abril() -> pd.DataFrame:
    _asegurar_datos()
    return pd.read_parquet(_ruta("cac_abril.parquet"))


@st.cache_data
def riesgo_cartera() -> pd.DataFrame:
    _asegurar_datos()
    return pd.read_parquet(_ruta("riesgo_cartera.parquet"))


@st.cache_data
def var_factores() -> pd.DataFrame:
    _asegurar_datos()
    return pd.read_parquet(_ruta("var_factores.parquet"))


@st.cache_data
def var_correlacion() -> pd.DataFrame:
    _asegurar_datos()
    return pd.read_parquet(_ruta("var_correlacion.parquet"))
