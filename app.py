"""
app.py — Portal de Análisis Financiero del Sector Solidario.

Dashboard multi-página sobre los estados financieros publicados por la
Superintendencia de Economía Solidaria (corte marzo 2026; ahorro y crédito
a abril 2026).

Arrancar:  streamlit run app.py
"""
import streamlit as st

from views import ahorro_credito, comparador, explorador, panorama, riesgo

st.set_page_config(
    page_title="Sector Solidario · Análisis Financiero",
    page_icon="📊",
    layout="wide",
)

# Ajuste fino: reduce la tipografía de las métricas para que las cifras (p. ej.
# "$61.8 B") no se trunquen en columnas estrechas de pantallas pequeñas.
st.markdown(
    """
    <style>
      [data-testid="stMetricValue"] { font-size: 1.4rem; }
      [data-testid="stMetricLabel"] p { font-size: 0.8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

paginas = [
    st.Page(panorama.render, title="Panorama del sector", icon="📈",
            url_path="panorama", default=True),
    st.Page(explorador.render, title="Explorador de entidades", icon="🔍",
            url_path="explorador"),
    st.Page(ahorro_credito.render, title="Ahorro y crédito", icon="💰",
            url_path="ahorro-credito"),
    st.Page(riesgo.render, title="Riesgo y supervisión", icon="⚠️",
            url_path="riesgo"),
    st.Page(comparador.render, title="Comparador", icon="⚖️",
            url_path="comparador"),
]

with st.sidebar:
    st.title("📊 Sector Solidario")
    st.caption("Análisis financiero · Supersolidaria")

nav = st.navigation(paginas)
nav.run()

with st.sidebar:
    st.divider()
    st.caption("Fuente: Superintendencia de Economía Solidaria. "
               "Corte 31/03/2026 (ahorro y crédito: 30/04/2026).")
