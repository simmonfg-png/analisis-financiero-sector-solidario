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


@st.cache_data(show_spinner="Cargando saldos a 6 dígitos…")
def saldos_6dig() -> pd.DataFrame:
    _asegurar_datos()
    return pd.read_parquet(_ruta("saldos_6dig.parquet"))


def historico_disponible() -> bool:
    """True si existe el parquet del histórico CAC (se genera con
    `python -m src.etl_historico` a partir de los Excel mensuales)."""
    return os.path.exists(_ruta("historico_cac.parquet"))


@st.cache_data(show_spinner="Cargando histórico CAC (5.4 M de saldos)…")
def historico() -> pd.DataFrame:
    return pd.read_parquet(_ruta("historico_cac.parquet"))


@st.cache_data
def historico_cuentas() -> pd.DataFrame:
    return pd.read_parquet(_ruta("historico_cuentas.parquet"))


@st.cache_data
def historico_entidades() -> pd.DataFrame:
    return pd.read_parquet(_ruta("historico_entidades.parquet"))


def historico_asociados_disponible() -> bool:
    """True si existe el histórico de número de asociados (pendiente de cargar).
    Formato esperado: largo con columnas PERIODO · CODIGO ENTIDAD · ASOCIADOS."""
    return os.path.exists(_ruta("historico_asociados.parquet"))


@st.cache_data
def historico_asociados() -> pd.DataFrame:
    return pd.read_parquet(_ruta("historico_asociados.parquet"))


@st.cache_data
def clasificacion_cac() -> pd.DataFrame:
    """Clasificación fija por categoría/subcategoría (período de referencia
    en `analytics.CATEGORIA_REF_PERIODO`). No depende del corte visualizado."""
    from src import analytics as an
    return an.clasificar_cac(historico())


@st.cache_data(show_spinner="Calculando panel mensual del sector…")
def historico_panel() -> pd.DataFrame:
    """Panel PERIODO × CUENTA del sector CAC completo (saldos sumados sobre
    todas las entidades). Base para las agrupaciones a nivel sector."""
    from src import analytics as an
    return an.panel_mensual(historico())


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
