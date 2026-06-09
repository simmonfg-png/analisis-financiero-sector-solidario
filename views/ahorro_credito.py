"""Ahorro y crédito — tasas activas/pasivas y márgenes de intermediación."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src import data
from src.format import pct

PALETA = px.colors.qualitative.Set2


def render():
    st.header("💰 Cooperativas de ahorro y crédito")
    st.caption("Tasas promedio ponderadas reportadas a la Delegatura Financiera · marzo 2026")

    t = data.tasas().copy()

    with st.sidebar:
        st.subheader("Filtros")
        segs = sorted(t["SEGMENTO"].dropna().unique())
        sel_seg = st.multiselect("Segmento", segs, default=[])
    if sel_seg:
        t = t[t["SEGMENTO"].isin(sel_seg)]

    # ── KPIs de tasas ──────────────────────────────────────────────────────────
    c = st.columns(4)
    c[0].metric("Entidades", f"{len(t):,}")
    c[1].metric("Tasa activa media", pct(t["TASA_ACTIVA"].mean()))
    c[2].metric("Tasa pasiva media", pct(t["TASA_PASIVA"].mean()))
    c[3].metric("Margen medio", pct(t["MARGEN"].mean()))

    st.divider()

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Tasa activa vs. pasiva")
        fig = px.scatter(
            t, x="TASA_PASIVA", y="TASA_ACTIVA", color="SEGMENTO",
            hover_name="SIGLA", color_discrete_sequence=PALETA,
            labels={"TASA_PASIVA": "Tasa pasiva (%)", "TASA_ACTIVA": "Tasa activa (%)"},
        )
        lo = float(min(t["TASA_PASIVA"].min(), t["TASA_ACTIVA"].min()))
        hi = float(max(t["TASA_PASIVA"].max(), t["TASA_ACTIVA"].max()))
        fig.add_shape(type="line", x0=lo, y0=lo, x1=hi, y1=hi,
                      line=dict(dash="dot", color="gray"))
        fig.update_layout(height=420, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")

    with g2:
        st.subheader("Margen por segmento")
        fig = px.box(t, x="SEGMENTO", y="MARGEN", color="SEGMENTO",
                     points="all", color_discrete_sequence=PALETA,
                     labels={"MARGEN": "Margen (pp)", "SEGMENTO": ""})
        fig.update_layout(height=420, showlegend=False, margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # ── Tasa activa por modalidad ──────────────────────────────────────────────
    st.subheader("Tasa activa media por modalidad")
    modal = {"ACT_CONSUMO": "Consumo", "ACT_VIVIENDA": "Vivienda",
             "ACT_COMERCIAL": "Comercial", "ACT_MICROCREDITO": "Microcrédito"}
    filas = [{"Modalidad": v, "Tasa": t[t[k] > 0][k].mean()}
             for k, v in modal.items() if k in t.columns]
    fig = px.bar(filas, x="Modalidad", y="Tasa", text="Tasa",
                 color="Modalidad", color_discrete_sequence=PALETA)
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(height=340, showlegend=False, margin=dict(t=10),
                      yaxis_title="Tasa (%)")
    st.plotly_chart(fig, width="stretch")

    # ── Rankings ───────────────────────────────────────────────────────────────
    st.subheader("Mayor y menor margen de intermediación")
    r1, r2 = st.columns(2)
    cols = ["SIGLA", "SEGMENTO", "TASA_ACTIVA", "TASA_PASIVA", "MARGEN"]
    with r1:
        st.caption("Mayor margen")
        st.dataframe(t.nlargest(10, "MARGEN")[cols], width="stretch",
                     hide_index=True)
    with r2:
        st.caption("Menor margen")
        st.dataframe(t.nsmallest(10, "MARGEN")[cols], width="stretch",
                     hide_index=True)
