"""Panorama CAC — visión macro de las cooperativas de ahorro y crédito.

Inspirado en el tablero de "Principales cifras" de la Superintendencia:
selector de fecha de corte (cualquier mes del histórico), pestañas y KPIs
con variación a 12 meses. Cifras financieras desde el histórico mensual; del
reporte de cuentas principales solo se usa ASOCIADOS y los metadatos de
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

# Colores de las cifras destacadas (estilo del tablero de referencia)
C_ACT, C_CAR, C_DEP, C_PAT = "#E8730C", "#B5179E", "#1F8A8A", "#3A0CA3"

# Cuentas principales y sus nombres para el glosario
NOMBRES = {
    "100000": "Activo", "200000": "Pasivo", "300000": "Patrimonio",
    "140000": "Cartera de créditos", "210000": "Depósitos",
    "350000": "Excedentes y/o pérdidas del ejercicio",
}


def _hero(col, label, value, color, sub=None):
    """Cifra destacada con número grande de color (al estilo del tablero)."""
    col.markdown(
        f"<div style='line-height:1.15'>"
        f"<div style='font-size:0.82rem;color:#666'>{label}</div>"
        f"<div style='font-size:1.95rem;font-weight:700;color:{color}'>{value}</div>"
        + (f"<div style='font-size:0.8rem;color:#888'>{sub}</div>" if sub else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def _ratio_serie(serie, num, den):
    return (serie[num] / serie[den] * 100).where(serie[den] != 0)


def render():
    st.markdown("### 📈 Panorama CAC")
    st.caption("Principales cifras de las cooperativas de ahorro y crédito · "
               "Superintendencia de Economía Solidaria")

    if not data.historico_disponible():
        st.warning("El histórico no está generado. Ejecuta `python -m src.etl_historico`.")
        return

    h = data.historico()
    meta = data.entidades()
    meta = meta[meta["TIPO ENTIDAD"].isin(TIPOS_CAC)][META_COLS]
    periodos = sorted(h["PERIODO"].astype(str).unique(), reverse=True)

    # ── Selector de fecha de corte (en el cuerpo, como en la referencia) ────────
    sc = st.columns([1, 3])
    corte = sc[0].selectbox("📅 Fecha de corte", periodos, index=0)

    # ── Filtros (barra lateral) ────────────────────────────────────────────────
    foto, _ = an.foto_cac(h, meta, corte)
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

    # Serie del subconjunto filtrado, hasta el corte elegido (para variación 12M)
    h_f = h if len(f) == len(foto) else h[h["CODIGO ENTIDAD"].isin(f["CODIGO ENTIDAD"])]
    serie = an.serie_historica(h_f, an.CUENTAS_FOTO)
    serie = serie[serie.index <= corte]

    def delta(cuenta):
        var = an.variacion_anual(serie[cuenta].dropna()) if cuenta in serie else float("nan")
        return f"{var:+.1f}% en 12 meses" if var == var else None

    sc[0].caption(f"**{len(f)}** cooperativas reportan en **{corte}**")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Principales cifras", "Activo · Pasivo", "Indicadores", "Glosario"])

    # ── TAB 1 · Principales cifras ──────────────────────────────────────────────
    with tab1:
        hero = st.columns(3)
        _hero(hero[0], "Activos totales", pesos(f["100000"].sum()), C_ACT, delta("100000"))
        _hero(hero[1], "Cartera de créditos", pesos(f["140000"].sum()), C_CAR, delta("140000"))
        _hero(hero[2], "Depósitos", pesos(f["210000"].sum()), C_DEP, delta("210000"))
        st.divider()

        k = st.columns(4)
        k[0].metric("Patrimonio", pesos(f["300000"].sum()), delta=delta("300000"))
        k[1].metric("Pasivos", pesos(f["200000"].sum()), delta=delta("200000"))
        k[2].metric("Excedentes", pesos(f["350000"].sum()),
                    help="Excedentes y/o pérdidas acumuladas del ejercicio")
        solv = f["300000"].sum() / f["100000"].sum() * 100 if f["100000"].sum() else 0
        k[3].metric("Solvencia", pct(solv), help="Patrimonio / Activo")
        k = st.columns(4)
        k[0].metric("Cooperativas", miles(len(f)))
        k[1].metric("Asociados", cantidad(f["ASOCIADOS"].sum()),
                    help="Del reporte de cuentas principales (corte marzo 2026)")
        cart_act = f["140000"].sum() / f["100000"].sum() * 100 if f["100000"].sum() else 0
        k[2].metric("Cartera / Activo", pct(cart_act))
        dep_act = f["210000"].sum() / f["100000"].sum() * 100 if f["100000"].sum() else 0
        k[3].metric("Depósitos / Activo", pct(dep_act))
        st.caption(GLOSARIO)

    # ── TAB 2 · Activo · Pasivo ─────────────────────────────────────────────────
    with tab2:
        st.subheader("Evolución de las cuentas de balance")
        evol = serie[["100000", "200000", "300000"]].rename(
            columns={"100000": "Activo", "200000": "Pasivo", "300000": "Patrimonio"})
        largo = evol.reset_index().melt(id_vars="PERIODO", var_name="Cuenta",
                                        value_name="VALOR")
        fig = px.line(largo, x="PERIODO", y="VALOR", color="Cuenta",
                      color_discrete_sequence=[C_ACT, C_PAT, C_DEP],
                      labels={"PERIODO": "", "VALOR": "Saldo (COP)"})
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Activos por departamento (top 10)")
            por_dep = an.por_grupo(f, "DEPARTAMENTO", top=10)
            fig = px.bar(por_dep, x="activo", y="DEPARTAMENTO", orientation="h",
                         text="entidades", color="activo", color_continuous_scale="Teal",
                         labels={"activo": "Activos (COP)", "DEPARTAMENTO": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=380,
                              coloraxis_showscale=False, margin=dict(l=0, r=0, t=10, b=0))
            fig.update_traces(texttemplate="%{text} coop.", textposition="outside")
            st.plotly_chart(fig, width="stretch")
        with g2:
            st.subheader("Especializadas vs. multiactivas")
            por_tipo = an.por_grupo(f, "TIPO ENTIDAD")
            por_tipo["Tipo"] = por_tipo["TIPO ENTIDAD"].str.replace(
                " de ahorro y credito", "", regex=False).str.replace(
                " con ahorro y credito", "s c/ ahorro", regex=False)
            fig = px.pie(por_tipo, names="Tipo", values="activo", hole=0.45,
                         color_discrete_sequence=PALETA)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=320, margin=dict(t=10, b=0), showlegend=False)
            st.plotly_chart(fig, width="stretch")
            st.caption(f"{int(por_tipo['entidades'].sum())} cooperativas · " + " · ".join(
                f"{int(r['entidades'])} {r['Tipo'].lower()}"
                for _, r in por_tipo.iterrows()))

    # ── TAB 3 · Indicadores ─────────────────────────────────────────────────────
    with tab3:
        st.subheader("Profundización financiera del sector")
        p = st.columns(3)
        p[0].metric("Cartera / Activo", pct(_ratio_serie(serie, "140000", "100000").iloc[-1]),
                    help="Qué tanto del activo está colocado en crédito")
        p[1].metric("Depósitos / Activo", pct(_ratio_serie(serie, "210000", "100000").iloc[-1]),
                    help="Fondeo vía captación de ahorro")
        p[2].metric("Solvencia (Patrimonio / Activo)",
                    pct(_ratio_serie(serie, "300000", "100000").iloc[-1]))

        ratios = serie.assign(
            **{"Cartera / Activo": _ratio_serie(serie, "140000", "100000"),
               "Depósitos / Activo": _ratio_serie(serie, "210000", "100000"),
               "Solvencia": _ratio_serie(serie, "300000", "100000")})
        largo = ratios[["Cartera / Activo", "Depósitos / Activo", "Solvencia"]] \
            .reset_index().melt(id_vars="PERIODO", var_name="Indicador", value_name="pct")
        fig = px.line(largo, x="PERIODO", y="pct", color="Indicador",
                      color_discrete_sequence=[C_CAR, C_DEP, C_PAT],
                      labels={"PERIODO": "", "pct": "%"})
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")

        st.divider()
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
            filas = [{"Tramo": etq, "% activos":
                      ff.head(n)["100000"].sum() / total * 100 if total else 0}
                     for etq, n in {"Top 10": 10, "Top 25": 25, "Top 50": 50}.items()]
            conc = px.bar(filas, x="Tramo", y="% activos", text="% activos",
                          color_discrete_sequence=PALETA)
            conc.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            conc.update_layout(height=320, yaxis_range=[0, 100], margin=dict(t=10))
            st.plotly_chart(conc, width="stretch")
            n_top = next((i + 1 for i in range(len(ff))
                          if ff.head(i + 1)["100000"].sum() >= total / 2), len(ff))
            st.info(f"El **50% de los activos** se concentra en **{n_top} cooperativas** "
                    f"de {len(ff):,}.")

    # ── TAB 4 · Glosario ────────────────────────────────────────────────────────
    with tab4:
        st.subheader("Glosario")
        st.markdown(
            "- **Activo** (100000): total de bienes y derechos de la cooperativa.\n"
            "- **Pasivo** (200000): obligaciones con terceros (incluye los depósitos).\n"
            "- **Patrimonio** (300000): aportes sociales, reservas y excedentes.\n"
            "- **Cartera de créditos** (140000): saldo de los créditos colocados.\n"
            "- **Depósitos** (210000): ahorros captados de los asociados.\n"
            "- **Excedentes** (350000): resultado acumulado del ejercicio.\n"
            "- **Solvencia**: Patrimonio / Activo. Colchón patrimonial frente al activo.\n"
            "- **Cartera / Activo**: proporción del activo colocada en crédito.\n"
            "- **Depósitos / Activo**: grado de fondeo con ahorro de asociados.\n"
            "- **Variación 12 meses**: cambio frente al mismo mes del año anterior.")
        st.caption(GLOSARIO)
        st.caption("Universo: cooperativas de ahorro y crédito (especializadas y "
                   "multiactivas con sección de ahorro). Cifras financieras del "
                   "histórico mensual de la Supersolidaria; asociados del reporte "
                   "de cuentas principales.")
