"""Panorama CAC — visión macro de las cooperativas de ahorro y crédito.

Cifras financieras: histórico mensual CAC (último corte). Del reporte de
cuentas principales solo se usa la columna ASOCIADOS y los metadatos de
identificación (nombre, sigla, departamento, tipo).
"""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src import analytics as an
from src import data
from src.format import GLOSARIO, cantidad, miles, pesos, pct

PALETA = px.colors.qualitative.Set2

TIPOS_CAC = ["Especializada de ahorro y credito", "Multiactiva con ahorro y credito"]
META_COLS = ["CODIGO ENTIDAD", "ENTIDAD", "SIGLA", "TIPO ENTIDAD",
             "DEPARTAMENTO", "MUNICIPIO", "ASOCIADOS"]


def render():
    st.header("📈 Panorama CAC")

    if not data.historico_disponible():
        st.warning("El histórico no está generado. Ejecuta `python -m src.etl_historico`.")
        return

    h = data.historico()
    meta = data.entidades()
    meta = meta[meta["TIPO ENTIDAD"].isin(TIPOS_CAC)][META_COLS]

    foto, corte = an.foto_cac(h, meta)
    st.caption(f"Cooperativas de ahorro y crédito · estados financieros "
               f"mensuales de la Supersolidaria · corte {corte}")

    # ── Filtros ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("Filtros")
        deptos = sorted(foto["DEPARTAMENTO"].dropna().unique())
        sel_dep = st.multiselect("Departamento", deptos, default=[])
        tipos = sorted(foto["TIPO ENTIDAD"].dropna().unique())
        sel_tipo = st.multiselect("Tipo de CAC", tipos, default=[])

    f = foto
    if sel_dep:
        f = f[f["DEPARTAMENTO"].isin(sel_dep)]
    if sel_tipo:
        f = f[f["TIPO ENTIDAD"].isin(sel_tipo)]
    if f.empty:
        st.info("Ningún resultado con los filtros elegidos.")
        return

    # serie del subconjunto filtrado, para las variaciones a 12 meses
    h_f = h if len(f) == len(foto) else h[h["CODIGO ENTIDAD"].isin(f["CODIGO ENTIDAD"])]
    serie = an.serie_historica(h_f, an.CUENTAS_FOTO)

    def delta(cuenta):
        var = an.variacion_anual(serie[cuenta].dropna()) if cuenta in serie else float("nan")
        return f"{var:+.1f}% en 12 meses" if var == var else None

    # ── KPIs ───────────────────────────────────────────────────────────────────
    c = st.columns(4)
    c[0].metric("Cooperativas", miles(len(f)),
                help="Entidades que reportaron en el último corte")
    c[1].metric("Activos", pesos(f["100000"].sum()), delta=delta("100000"))
    c[2].metric("Cartera", pesos(f["140000"].sum()), delta=delta("140000"),
                help="Cartera de créditos")
    c[3].metric("Depósitos", pesos(f["210000"].sum()), delta=delta("210000"))
    c = st.columns(4)
    c[0].metric("Patrimonio", pesos(f["300000"].sum()), delta=delta("300000"))
    c[1].metric("Excedentes", pesos(f["350000"].sum()),
                help="Excedentes acumulados del ejercicio")
    c[2].metric("Asociados", cantidad(f["ASOCIADOS"].sum()),
                help="Del reporte de cuentas principales (corte marzo 2026)")
    solv = f["300000"].sum() / f["100000"].sum() * 100 if f["100000"].sum() else 0
    c[3].metric("Solvencia", pct(solv), help="Patrimonio / Activo")
    st.caption(GLOSARIO)

    st.divider()

    # ── Activos por departamento y por tipo ────────────────────────────────────
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Activos por departamento (top 10)")
        por_dep = an.por_grupo(f, "DEPARTAMENTO", top=10)
        fig = px.bar(
            por_dep, x="activo", y="DEPARTAMENTO", orientation="h",
            text="entidades", color="activo", color_continuous_scale="Teal",
            labels={"activo": "Activos (COP)", "DEPARTAMENTO": ""},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400,
                          coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
        fig.update_traces(texttemplate="%{text} coop.", textposition="outside")
        st.plotly_chart(fig, width="stretch")

    with g2:
        st.subheader("Especializadas vs. multiactivas")
        por_tipo = an.por_grupo(f, "TIPO ENTIDAD")
        por_tipo["Tipo"] = por_tipo["TIPO ENTIDAD"].str.replace(
            " de ahorro y credito", "", regex=False).str.replace(
            " con ahorro y credito", "s con ahorro y crédito", regex=False)
        fig = px.pie(por_tipo, names="Tipo", values="activo", hole=0.45,
                     color_discrete_sequence=PALETA)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=300, margin=dict(t=10, b=0), showlegend=False)
        st.plotly_chart(fig, width="stretch")
        st.caption(f"{int(por_tipo['entidades'].sum())} cooperativas: " + " · ".join(
            f"{int(r['entidades'])} {r['Tipo'].lower()}" for _, r in por_tipo.iterrows()))

    st.divider()

    # ── Ranking + concentración ────────────────────────────────────────────────
    g3, g4 = st.columns([3, 2])
    with g3:
        st.subheader("Mayores cooperativas por activos")
        top = (f.sort_values("100000", ascending=False)
               .head(15)[["ENTIDAD", "SIGLA", "DEPARTAMENTO", "ASOCIADOS", "100000"]]
               .rename(columns={"100000": "Activos"}))
        top["Activos"] = top["Activos"].map(pesos)
        top["ASOCIADOS"] = top["ASOCIADOS"].map(miles)
        st.dataframe(top, width="stretch", hide_index=True)

    with g4:
        st.subheader("Concentración de activos")
        ff = f.sort_values("100000", ascending=False).reset_index(drop=True)
        total = ff["100000"].sum()
        filas = []
        for etq, n in {"Top 10": 10, "Top 25": 25, "Top 50": 50}.items():
            part = ff.head(n)["100000"].sum() / total * 100 if total else 0
            filas.append({"Tramo": etq, "% activos": part})
        conc = px.bar(filas, x="Tramo", y="% activos", text="% activos",
                      color_discrete_sequence=PALETA)
        conc.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        conc.update_layout(height=320, yaxis_range=[0, 100], margin=dict(t=10))
        st.plotly_chart(conc, width="stretch")
        n_top = next((i + 1 for i in range(len(ff))
                      if ff.head(i + 1)["100000"].sum() >= total / 2), len(ff))
        st.info(f"El **50% de los activos** se concentra en **{n_top} cooperativas** "
                f"de {len(ff):,}.")
