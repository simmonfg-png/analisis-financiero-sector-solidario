"""Panorama del sector — visión macro de las entidades vigiladas."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src import analytics as an
from src import data
from src.format import GLOSARIO, cantidad, miles, pesos, pct

PALETA = px.colors.qualitative.Set2


def render():
    st.header("📈 Panorama del sector solidario")
    st.caption("Estados financieros reportados a la Supersolidaria · corte 31 de marzo de 2026")

    df = data.entidades()

    # ── Filtros ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("Filtros")
        tipos = sorted(df["TIPO ENTIDAD"].unique())
        sel_tipos = st.multiselect("Tipo de entidad", tipos, default=[])
        deptos = sorted(df["DEPARTAMENTO"].unique())
        sel_dep = st.multiselect("Departamento", deptos, default=[])

    f = df.copy()
    if sel_tipos:
        f = f[f["TIPO ENTIDAD"].isin(sel_tipos)]
    if sel_dep:
        f = f[f["DEPARTAMENTO"].isin(sel_dep)]

    res = an.resumen_sector(f)

    # ── KPIs ───────────────────────────────────────────────────────────────────
    c = st.columns(4)
    c[0].metric("Entidades", miles(res["entidades"]))
    c[1].metric("Activos", pesos(res["activo"]))
    c[2].metric("Patrimonio", pesos(res["patrimonio"]))
    c[3].metric("Asociados", cantidad(res["asociados"]))
    c = st.columns(4)
    c[0].metric("Cartera", pesos(res["cartera"]), help="Cartera de créditos")
    c[1].metric("Depósitos", pesos(res["depositos"]))
    c[2].metric("Excedentes", pesos(res["excedente"]), help="Excedentes del periodo")
    solv = res["patrimonio"] / res["activo"] * 100 if res["activo"] else 0
    c[3].metric("Solvencia", pct(solv), help="Patrimonio / Activo")
    st.caption(GLOSARIO)

    st.divider()

    # ── Composición por tipo y por departamento ────────────────────────────────
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Activos por tipo de entidad")
        por_tipo = an.por_grupo(f, "TIPO ENTIDAD")
        fig = px.bar(
            por_tipo.head(10), x="activo", y="TIPO ENTIDAD", orientation="h",
            text="entidades", color_discrete_sequence=PALETA,
            labels={"activo": "Activos (COP)", "TIPO ENTIDAD": ""},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400,
                          margin=dict(l=0, r=0, t=10, b=0))
        fig.update_traces(texttemplate="%{text} ent.", textposition="outside")
        st.plotly_chart(fig, width="stretch")

    with g2:
        st.subheader("Activos por departamento (top 10)")
        por_dep = an.por_grupo(f, "DEPARTAMENTO", top=10)
        fig = px.bar(
            por_dep, x="activo", y="DEPARTAMENTO", orientation="h",
            color="activo", color_continuous_scale="Teal",
            labels={"activo": "Activos (COP)", "DEPARTAMENTO": ""},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400,
                          coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # ── Ranking + concentración ────────────────────────────────────────────────
    g3, g4 = st.columns([3, 2])
    with g3:
        st.subheader("Mayores entidades por activos")
        top = an.ranking(f, "100000", n=15)
        top = top.rename(columns={"100000": "Activos"})
        top["Activos"] = top["Activos"].map(pesos)
        st.dataframe(top, width="stretch", hide_index=True)

    with g4:
        st.subheader("Concentración de activos")
        ff = f.sort_values("100000", ascending=False).reset_index(drop=True)
        total = ff["100000"].sum()
        tramos = {"Top 10": 10, "Top 50": 50, "Top 100": 100}
        filas = []
        for etq, n in tramos.items():
            part = ff.head(n)["100000"].sum() / total * 100 if total else 0
            filas.append({"Tramo": etq, "% activos": part})
        conc = px.bar(filas, x="Tramo", y="% activos", text="% activos",
                      color_discrete_sequence=PALETA)
        conc.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        conc.update_layout(height=320, yaxis_range=[0, 100], margin=dict(t=10))
        st.plotly_chart(conc, width="stretch")
        n_top = next((i + 1 for i in range(len(ff))
                      if ff.head(i + 1)["100000"].sum() >= total / 2), len(ff))
        st.info(f"El **50% de los activos** se concentra en **{n_top} entidades** "
                f"de {len(ff):,}.")
