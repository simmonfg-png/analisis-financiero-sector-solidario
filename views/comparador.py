"""Comparador — benchmark de varias entidades lado a lado."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src import analytics as an
from src import data
from src.format import pesos, pct

METRICAS = {
    "ROA": "ROA del periodo (%)",
    "ROE": "ROE del periodo (%)",
    "SOLVENCIA": "Solvencia (%)",
    "ENDEUDAMIENTO": "Endeudamiento (%)",
    "CARTERA_ACTIVO": "Cartera / Activo (%)",
    "FONDEO_DEPOSITOS": "Fondeo por depósitos (%)",
    "MARGEN_EXCEDENTE": "Margen de excedente (%)",
    "EFICIENCIA": "Carga administrativa (%)",
}


def render():
    st.header("⚖️ Comparador de entidades")
    df = an.agregar_indicadores(data.entidades())
    nombres = (df["SIGLA"].replace("", None).fillna(df["ENTIDAD"])).tolist()
    df = df.assign(_etq=nombres)

    pre = df.nlargest(3, "100000")["_etq"].tolist()
    sel = st.multiselect("Entidades a comparar (2–6)", df["_etq"].tolist(),
                         default=pre, max_selections=6)
    if len(sel) < 2:
        st.info("Selecciona al menos dos entidades.")
        return

    sub = df[df["_etq"].isin(sel)]

    # ── Tabla comparativa ──────────────────────────────────────────────────────
    st.subheader("Cifras principales")
    filas = {
        "Activos": ("100000", pesos), "Patrimonio": ("300000", pesos),
        "Cartera": ("140000", pesos), "Depósitos": ("210000", pesos),
        "Excedentes": ("350000", pesos), "Asociados": ("ASOCIADOS", lambda v: f"{int(v):,}"),
    }
    tabla = {"Indicador": list(filas.keys())}
    for _, e in sub.iterrows():
        tabla[e["_etq"]] = [fmt(e[code]) for code, fmt in filas.values()]
    st.dataframe(tabla, width="stretch", hide_index=True)

    # ── Radar de indicadores ───────────────────────────────────────────────────
    st.subheader("Perfil de indicadores")
    metr = st.multiselect("Indicadores", list(METRICAS), default=list(METRICAS)[:5],
                          format_func=lambda k: METRICAS[k])
    if metr:
        long = sub.melt(id_vars="_etq", value_vars=metr, var_name="Indicador",
                        value_name="Valor")
        long["Indicador"] = long["Indicador"].map(METRICAS)
        fig = px.line_polar(long, r="Valor", theta="Indicador", color="_etq",
                            line_close=True, color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(fill="toself", opacity=0.5)
        fig.update_layout(height=480, margin=dict(t=30), legend_title="")
        st.plotly_chart(fig, width="stretch")

    # ── Barras por indicador ───────────────────────────────────────────────────
    foco = st.selectbox("Comparar un indicador", list(METRICAS),
                        format_func=lambda k: METRICAS[k])
    fig = px.bar(sub, x="_etq", y=foco, color="_etq", text=foco,
                 color_discrete_sequence=px.colors.qualitative.Set2,
                 labels={"_etq": "", foco: METRICAS[foco]})
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(height=380, showlegend=False, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
