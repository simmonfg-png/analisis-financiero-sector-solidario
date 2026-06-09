"""
app.py — Análisis Financiero del Sector Solidario.

Interfaz Streamlit: carga un balance publicado por la Superintendencia de
Economía Solidaria (Excel/CSV), calcula indicadores y los visualiza.

Arrancar:  streamlit run app.py
"""
import streamlit as st

from config import CUENTAS, ETIQUETAS
from src.loader import cargar_balance, saldo_de
from src.indicators import calcular_indicadores
from src.charts import torta_estructura, barras_indicadores

st.set_page_config(page_title="Análisis Sector Solidario", layout="wide")

st.title("📊 Análisis Financiero del Sector Solidario")
st.caption(
    "Carga un balance de la Superintendencia de Economía Solidaria y obtén "
    "indicadores y gráficas para la toma de decisiones."
)

archivo = st.file_uploader(
    "Sube el balance (Excel .xlsx/.xls o CSV)",
    type=["xlsx", "xls", "csv"],
)

if archivo is None:
    st.info("⬆️ Sube un archivo de balance para comenzar.")
    st.stop()

# ── Carga ─────────────────────────────────────────────────────────────────────
try:
    df = cargar_balance(archivo)
except Exception as e:
    st.error(f"No se pudo leer el archivo: {e}")
    st.stop()

st.success(f"✅ Balance cargado — {len(df):,} cuentas.")

# Diccionario {cuenta: saldo} para los indicadores
balance = {c: saldo_de(df, c) for c in CUENTAS.values()}
ind = calcular_indicadores(balance)

# ── Métricas principales ──────────────────────────────────────────────────────
st.subheader("Cifras del balance")
c1, c2, c3 = st.columns(3)
c1.metric(ETIQUETAS["activo"],     f"${ind['Activo']:,.0f}")
c2.metric(ETIQUETAS["pasivo"],     f"${ind['Pasivo']:,.0f}")
c3.metric(ETIQUETAS["patrimonio"], f"${ind['Patrimonio']:,.0f}")

# ── Indicadores ───────────────────────────────────────────────────────────────
st.subheader("Indicadores")
cols = st.columns(5)
for col, (k, v) in zip(cols, [(k, v) for k, v in ind.items() if k.endswith("(%)")]):
    col.metric(k.replace(" (%)", ""), f"{v:.2f}%")

# ── Gráficas ──────────────────────────────────────────────────────────────────
g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(
        torta_estructura(ind["Activo"], ind["Pasivo"], ind["Patrimonio"]),
        use_container_width=True,
    )
with g2:
    st.plotly_chart(barras_indicadores(ind), use_container_width=True)

# ── Detalle ───────────────────────────────────────────────────────────────────
with st.expander("Ver detalle del balance cargado"):
    st.dataframe(df, use_container_width=True, hide_index=True)
