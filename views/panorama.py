"""Panorama CAC — visión macro de las cooperativas de ahorro y crédito.

Inspirado en el tablero de "Principales cifras" de la Superintendencia:
selector de fecha de corte (cualquier mes del histórico), pestañas y KPIs con
variación a 12 meses. Las desagregaciones de cartera, depósitos, balance y
rentabilidad se calculan con el catálogo de agrupaciones PUC (`agrupaciones.py`)
aplicado al panel mensual del histórico (a 6 dígitos). Del reporte de cuentas
principales solo se usa ASOCIADOS y los metadatos de identificación.
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

# Modalidades de cartera y tipos de depósito (alias del catálogo de agrupaciones)
MODALIDADES = [
    ("CARTERA_BRUTA_CONSUMO_CAJA", "Consumo caja"),
    ("CARTERA_BRUTA_CONSUMO_LIBRANZA", "Consumo libranza"),
    ("CARTERA_BRUTA_COMERCIAL", "Comercial"),
    ("CARTERA_BRUTA_PRODUCTIVO", "Productivo"),
    ("CARTERA_BRUTA_VIVIENDA", "Vivienda"),
    ("CARTERA_BRUTA_MICROCREDITO", "Microcrédito"),
    ("CARTERA_BRUTA_EMPLEADOS", "Empleados"),
]
DEPOSITOS = [
    ("CDAT_NETO", "CDAT"),
    ("AHORRO_VISTA", "Ahorro a la vista"),
    ("AHORRO_CONTRACTUAL_NETO", "Ahorro contractual"),
]
# Composición del balance (alias → etiqueta)
ACTIVO_COMP = [
    ("CARTERA_NETA", "Cartera neta"), ("INVERSIONES_VISTA", "Inversiones"),
    ("EQUIVALENTES_EFECTIVO", "Equivalentes de efectivo"),
    ("CAPITAL_TRABAJO_IMPRODUCTIVO", "Caja y bancos"),
    ("ACTIVOS_FIJOS", "Activos fijos"), ("OTRAS_CUENTAS_POR_COBRAR", "Cuentas por cobrar"),
]
PATRIMONIO_COMP = [
    ("CAPITAL_SOCIAL", "Capital social"), ("CAPITAL_INSTITUCIONAL", "Capital institucional"),
    ("EXCEDENTE", "Excedente del ejercicio"),
]


def _hero(col, label, value, color, sub=None):
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


def _torta_alias(panel, corte, items, titulo):
    """Torta de la composición (alias → monto) en el corte."""
    datos = [{"Concepto": etq, "Valor": an.valor_alias(panel, corte, a)} for a, etq in items]
    datos = [d for d in datos if d["Valor"] and d["Valor"] > 0]
    st.subheader(titulo)
    if not datos:
        st.caption("Sin datos para este corte.")
        return
    fig = px.pie(datos, names="Concepto", values="Valor", hole=0.45,
                 color_discrete_sequence=PALETA)
    fig.update_traces(textposition="inside", textinfo="percent")
    fig.update_layout(height=330, margin=dict(t=10, b=0), legend_font_size=11)
    st.plotly_chart(fig, width="stretch")


def _area_modalidades(panel, items, titulo):
    """Área apilada de la evolución de una composición (alias → monto)."""
    df = panel.index.to_frame(name="PERIODO")
    for a, etq in items:
        df[etq] = an.serie_alias(panel, a).values
    cols = [etq for _, etq in items if df[etq].abs().sum() > 0]
    largo = df.melt(id_vars="PERIODO", value_vars=cols,
                    var_name="Concepto", value_name="VALOR")
    st.subheader(titulo)
    fig = px.area(largo, x="PERIODO", y="VALOR", color="Concepto",
                  color_discrete_sequence=PALETA, labels={"PERIODO": "", "VALOR": "COP"})
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0),
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, width="stretch")


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

    sc = st.columns([1, 3])
    corte = sc[0].selectbox("📅 Fecha de corte", periodos, index=0)

    foto, _ = an.foto_cac(h, meta, corte)
    # Clasificación FIJA (no depende del corte; ver analytics.CATEGORIA_REF_PERIODO)
    clasif = data.clasificacion_cac()
    foto = foto.merge(clasif[["CODIGO ENTIDAD", "CATEGORIA", "SUBCATEGORIA"]],
                      on="CODIGO ENTIDAD", how="left")
    with st.sidebar:
        st.subheader("Filtros")
        deptos = sorted(foto["DEPARTAMENTO"].dropna().unique())
        sel_dep = st.multiselect("Departamento", deptos, default=[])
        # los municipios disponibles dependen del departamento elegido
        base_mun = foto[foto["DEPARTAMENTO"].isin(sel_dep)] if sel_dep else foto
        munis = sorted(base_mun["MUNICIPIO"].dropna().unique())
        sel_mun = st.multiselect("Municipio", munis, default=[])
        sel_cat = st.multiselect(
            "Categoría", ["Básica", "Intermedia", "Plena"], default=[],
            help="Por monto de activos (Art. 2.11.13.1.2): Básica ≤ 315M UVR · "
                 "Intermedia hasta 1.400M UVR · Plena > 1.400M UVR. Clasificación "
                 "fija con los activos a dic-2024; se actualiza por código.")
        # las subcategorías disponibles dependen de la categoría elegida
        cats_sub = sel_cat or ["Básica", "Intermedia", "Plena"]
        sub_opts = [s for c in ["Básica", "Intermedia", "Plena"] if c in cats_sub
                    for s in an.SUBCATEGORIAS[c]]
        sel_sub = st.multiselect(
            "Subcategoría", sub_opts, default=[],
            help="Tamaño dentro de la categoría. Intermedia: 2 grupos partidos en "
                 "el punto medio (~$323 mM). Básica: 3 grupos por tercios del tope "
                 "(~$39 mM y ~$79 mM). Plena no se subdivide.")

    f = foto
    if sel_dep:
        f = f[f["DEPARTAMENTO"].isin(sel_dep)]
    if sel_mun:
        f = f[f["MUNICIPIO"].isin(sel_mun)]
    if sel_cat:
        f = f[f["CATEGORIA"].isin(sel_cat)]
    if sel_sub:
        f = f[f["SUBCATEGORIA"].isin(sel_sub)]
    if f.empty:
        st.info("Ningún resultado con los filtros elegidos.")
        return

    filtrado = len(f) < len(foto)
    serie = an.serie_historica(
        h if not filtrado else h[h["CODIGO ENTIDAD"].isin(f["CODIGO ENTIDAD"])],
        an.CUENTAS_FOTO)
    serie = serie[serie.index <= corte]

    # Panel mensual (PERIODO × CUENTA) para las agrupaciones, recortado al corte
    panel = (data.historico_panel() if not filtrado
             else an.panel_mensual(h, f["CODIGO ENTIDAD"]))
    panel = panel[panel.index <= corte]

    def delta(cuenta):
        var = an.variacion_anual(serie[cuenta].dropna()) if cuenta in serie else float("nan")
        return f"{var:+.1f}% en 12 meses" if var == var else None

    def va(alias):  # valor de agrupación en el corte
        return an.valor_alias(panel, corte, alias)

    sc[0].caption(f"**{len(f)}** cooperativas reportan en **{corte}**")

    tabs = st.tabs(["Principales cifras", "Balance", "Cartera",
                    "Depósitos y fondeo", "Rentabilidad", "Glosario"])

    # ── TAB 1 · Principales cifras ──────────────────────────────────────────────
    with tabs[0]:
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
        k[2].metric("Cartera / Activo",
                    pct(f["140000"].sum() / f["100000"].sum() * 100 if f["100000"].sum() else 0))
        k[3].metric("Depósitos / Activo",
                    pct(f["210000"].sum() / f["100000"].sum() * 100 if f["100000"].sum() else 0))
        st.caption(GLOSARIO)

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
            conc.update_layout(height=300, yaxis_range=[0, 100], margin=dict(t=10))
            st.plotly_chart(conc, width="stretch")
            n_top = next((i + 1 for i in range(len(ff))
                          if ff.head(i + 1)["100000"].sum() >= total / 2), len(ff))
            st.info(f"El **50% de los activos** está en **{n_top}** cooperativas de {len(ff):,}.")

    # ── TAB 2 · Balance ─────────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Evolución de las cuentas de balance")
        evol = serie[["100000", "200000", "300000"]].rename(
            columns={"100000": "Activo", "200000": "Pasivo", "300000": "Patrimonio"})
        largo = evol.reset_index().melt(id_vars="PERIODO", var_name="Cuenta",
                                        value_name="VALOR")
        fig = px.line(largo, x="PERIODO", y="VALOR", color="Cuenta",
                      color_discrete_sequence=[C_ACT, C_PAT, C_DEP],
                      labels={"PERIODO": "", "VALOR": "Saldo (COP)"})
        fig.update_layout(height=360, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, width="stretch")

        b1, b2 = st.columns(2)
        with b1:
            _torta_alias(panel, corte, ACTIVO_COMP, "Composición del activo")
        with b2:
            _torta_alias(panel, corte, PATRIMONIO_COMP, "Composición del patrimonio")

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Activos por departamento (top 10)")
            por_dep = an.por_grupo(f, "DEPARTAMENTO", top=10)
            fig = px.bar(por_dep, x="activo", y="DEPARTAMENTO", orientation="h",
                         text="entidades", color="activo", color_continuous_scale="Teal",
                         labels={"activo": "Activos (COP)", "DEPARTAMENTO": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=360,
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

    # ── TAB 3 · Cartera ─────────────────────────────────────────────────────────
    with tabs[2]:
        cb = va("CARTERA_BRUTA")
        ri = va("CARTERA_EN_RIESGO")
        pr = va("PROVISIONES_TOTAL")
        k = st.columns(4)
        _hero(k[0], "Cartera bruta", pesos(cb), C_CAR)
        k[1].metric("Cartera en riesgo (B-E)", pesos(ri),
                    help="Capital + intereses en categorías B a E")
        k[2].metric("Calidad por riesgo", pct(ri / cb * 100 if cb else float("nan")),
                    help="Cartera en riesgo / cartera bruta")
        k[3].metric("Cobertura por riesgo", pct(pr / ri * 100 if ri else float("nan")),
                    help="Provisiones totales / cartera en riesgo")

        c1, c2 = st.columns(2)
        with c1:
            _torta_alias(panel, corte, MODALIDADES, "Composición por modalidad")
        with c2:
            st.subheader("Calidad y cobertura en el tiempo")
            calidad = an.ratio_alias(panel, "CARTERA_EN_RIESGO", "CARTERA_BRUTA")
            cobertura = an.ratio_alias(panel, "PROVISIONES_TOTAL", "CARTERA_EN_RIESGO")
            comp = calidad.to_frame("Calidad por riesgo")
            comp["Cobertura por riesgo"] = cobertura
            largo = comp.reset_index().melt(id_vars="PERIODO", var_name="Indicador",
                                            value_name="pct")
            fig = px.line(largo, x="PERIODO", y="pct", color="Indicador",
                          color_discrete_sequence=[C_CAR, C_DEP],
                          labels={"PERIODO": "", "pct": "%"})
            fig.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=0),
                              legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, width="stretch")

        _area_modalidades(panel, MODALIDADES, "Evolución de la cartera por modalidad")

    # ── TAB 4 · Depósitos y fondeo ──────────────────────────────────────────────
    with tabs[3]:
        dep_total = sum(va(a) for a, _ in DEPOSITOS)
        k = st.columns(4)
        _hero(k[0], "Depósitos (sin intereses)", pesos(dep_total), C_DEP)
        k[1].metric("Aportes sociales", pesos(va("APORTES_SOCIALES_ASOCIADOS")))
        k[2].metric("Oblig. financieras", pesos(va("OBLIGACIONES_FINANCIERAS")),
                    help="Créditos obtenidos de otras entidades")
        cb = va("CARTERA_BRUTA")
        k[3].metric("Depósitos / Cartera", pct(va("DEPOSITOS_NETOS") / cb * 100 if cb else float("nan")),
                    help="Qué parte de la cartera se fondea con ahorro")

        d1, d2 = st.columns(2)
        with d1:
            st.subheader("Depósitos por tipo")
            datos = [{"Tipo": etq, "Valor": va(a)} for a, etq in DEPOSITOS]
            datos = [x for x in datos if x["Valor"] and x["Valor"] > 0]
            fig = px.bar(sorted(datos, key=lambda x: x["Valor"]),
                         x="Valor", y="Tipo", orientation="h",
                         color_discrete_sequence=[C_DEP], labels={"Valor": "COP", "Tipo": ""})
            fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, width="stretch")
        with d2:
            _area_modalidades(panel, DEPOSITOS, "Evolución de los depósitos por tipo")

        st.subheader("Estructura de fondeo de la cartera (en el tiempo)")
        fdep = an.ratio_alias(panel, "DEPOSITOS_NETOS", "CARTERA_BRUTA")
        fapo = an.ratio_alias(panel, "APORTES_SOCIALES_ASOCIADOS", "CARTERA_BRUTA")
        comp = fdep.to_frame("Depósitos / Cartera")
        comp["Aportes / Cartera"] = fapo
        largo = comp.reset_index().melt(id_vars="PERIODO", var_name="Fuente", value_name="pct")
        fig = px.line(largo, x="PERIODO", y="pct", color="Fuente",
                      color_discrete_sequence=[C_DEP, C_PAT], labels={"PERIODO": "", "pct": "%"})
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")

    # ── TAB 5 · Rentabilidad ────────────────────────────────────────────────────
    with tabs[4]:
        roa, roe = an.roa_roe(panel)
        ing = va("INGRESOS_CARTERA")
        cf = va("COSTOS_FINANCIEROS")
        ga = va("GASTOS_ADMINISTRACION")
        margen_fin = (ing - cf) / ing * 100 if ing else float("nan")
        eficiencia = ga / ing * 100 if ing else float("nan")
        k = st.columns(4)
        k[0].metric("ROA (anualizado)", pct(roa.iloc[-1]), help="Excedente / Activo, anualizado")
        k[1].metric("ROE (anualizado)", pct(roe.iloc[-1]), help="Excedente / Patrimonio, anualizado")
        k[2].metric("Margen financiero", pct(margen_fin),
                    help="(Ingresos de cartera − costos financieros) / ingresos de cartera")
        k[3].metric("Eficiencia (gastos/ingresos)", pct(eficiencia),
                    help="Gastos de administración / ingresos de cartera")

        st.subheader("ROA y ROE anualizados en el tiempo")
        comp = roa.to_frame("ROA").assign(ROE=roe)
        largo = comp.reset_index().melt(id_vars="PERIODO", var_name="Indicador", value_name="pct")
        fig = px.line(largo, x="PERIODO", y="pct", color="Indicador",
                      color_discrete_sequence=[C_ACT, C_PAT], labels={"PERIODO": "", "pct": "%"})
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")
        st.caption("El excedente del histórico es acumulado del año; ROA y ROE se "
                   "anualizan dividiendo por los meses corridos (puede oscilar a "
                   "comienzos de cada año).")

        st.subheader("Margen financiero y eficiencia en el tiempo")
        margen = ((an.serie_alias(panel, "INGRESOS_CARTERA")
                   - an.serie_alias(panel, "COSTOS_FINANCIEROS"))
                  / an.serie_alias(panel, "INGRESOS_CARTERA") * 100)
        efi = an.ratio_alias(panel, "GASTOS_ADMINISTRACION", "INGRESOS_CARTERA")
        comp = margen.to_frame("Margen financiero")
        comp["Eficiencia (gastos/ingresos)"] = efi
        largo = comp.reset_index().melt(id_vars="PERIODO", var_name="Indicador", value_name="pct")
        fig = px.line(largo, x="PERIODO", y="pct", color="Indicador",
                      color_discrete_sequence=[C_DEP, C_CAR], labels={"PERIODO": "", "pct": "%"})
        fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0),
                          legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, width="stretch")

    # ── TAB 6 · Glosario ────────────────────────────────────────────────────────
    with tabs[5]:
        st.subheader("Glosario")
        st.markdown(
            "- **Activo / Pasivo / Patrimonio**: clases 1, 2 y 3 del PUC.\n"
            "- **Cartera bruta**: capital colocado por todas las modalidades.\n"
            "- **Cartera en riesgo (B-E)**: saldo en categorías B a E (capital + intereses).\n"
            "- **Calidad por riesgo**: cartera en riesgo / cartera bruta.\n"
            "- **Cobertura por riesgo**: provisiones totales / cartera en riesgo.\n"
            "- **Modalidades**: consumo (caja/libranza), comercial, vivienda, "
            "microcrédito, productivo, empleados.\n"
            "- **Depósitos por tipo**: ahorro a la vista, CDAT, ahorro contractual "
            "(netos de intereses causados).\n"
            "- **Depósitos / Cartera**: grado de fondeo de la cartera con ahorro.\n"
            "- **ROA / ROE**: excedente sobre activo / patrimonio, anualizado.\n"
            "- **Margen financiero**: (ingresos de cartera − costos financieros) / "
            "ingresos de cartera.\n"
            "- **Eficiencia**: gastos de administración / ingresos de cartera.\n"
            "- **Variación 12 meses**: cambio frente al mismo mes del año anterior.")
        st.caption(GLOSARIO)
        st.caption("Universo: cooperativas de ahorro y crédito (especializadas y "
                   "multiactivas con sección de ahorro). Cifras del histórico mensual "
                   "a 6 dígitos; desagregaciones vía catálogo de agrupaciones PUC.")
