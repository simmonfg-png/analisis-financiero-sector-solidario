"""Riesgo / Supervisión — indicador de cartera vs. umbrales σ y VaR de mercado."""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data
from src.format import pct


def render():
    st.header("⚠️ Riesgo y supervisión")

    tab1, tab2 = st.tabs(["Indicador de cartera (σ)", "Riesgo de mercado (VaR)"])

    # ── Indicador de cartera vs umbrales ───────────────────────────────────────
    with tab1:
        r = data.riesgo_cartera()
        ult = r.iloc[-1]
        c = st.columns(4)
        c[0].metric("Último indicador", pct(ult["INDICADOR_CARTERA"] * 100, 2),
                    help=f"Periodo: {ult['PERIODO']}")
        c[1].metric("Desviación estándar", pct(ult["DESV_ESTANDAR"] * 100, 2))
        if "PROM_MAS_1_SIGMA" in r.columns:
            c[2].metric("Umbral +1σ", pct(ult["PROM_MAS_1_SIGMA"] * 100, 2))
        if "PROM_MAS_2_SIGMA" in r.columns:
            c[3].metric("Umbral +2σ", pct(ult["PROM_MAS_2_SIGMA"] * 100, 2))

        st.subheader("Evolución del indicador de cartera y umbrales de alerta")
        fig = go.Figure()
        x = r["PERIODO"]
        fig.add_trace(go.Scatter(x=x, y=r["INDICADOR_CARTERA"], name="Indicador",
                                 mode="lines+markers", line=dict(width=3, color="#1f77b4")))
        if "PROM_MAS_1_SIGMA" in r.columns:
            fig.add_trace(go.Scatter(x=x, y=r["PROM_MAS_1_SIGMA"], name="+1σ",
                                     line=dict(dash="dash", color="orange")))
        if "PROM_MAS_2_SIGMA" in r.columns:
            fig.add_trace(go.Scatter(x=x, y=r["PROM_MAS_2_SIGMA"], name="+2σ",
                                     line=dict(dash="dot", color="red")))
        fig.update_layout(height=440, yaxis_tickformat=".1%", margin=dict(t=10),
                          legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, width="stretch")
        st.info("Las bandas **+1σ y +2σ** marcan el rango esperado del indicador de "
                "cartera del subsector. Cruzar el umbral +2σ es una señal de alerta "
                "de deterioro de la calidad de cartera.")

    # ── VaR de mercado ─────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Factores de riesgo de mercado")
        f = data.var_factores()
        st.caption("Medias y desviaciones de los factores (TES COP / UVR) · marzo 2026")
        st.dataframe(f, width="stretch", hide_index=True)

        st.subheader("Matriz de correlación entre factores")
        corr = data.var_correlacion().set_index("FACTOR")
        fig = px.imshow(corr, text_auto=".2f", aspect="auto",
                        color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        fig.update_layout(height=600, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")
        st.info("La matriz de correlación y las desviaciones de los factores son los "
                "insumos para el cálculo del **Valor en Riesgo (VaR)** del portafolio "
                "de inversiones del sector.")
