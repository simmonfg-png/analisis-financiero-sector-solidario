"""Panorama CAC — visión macro de las cooperativas de ahorro y crédito.

Inspirado en el tablero de "Principales cifras" de la Superintendencia:
selector de fecha de corte (cualquier mes del histórico), pestañas y KPIs con
variación a 12 meses. Las desagregaciones de cartera, depósitos, balance y
rentabilidad se calculan con el catálogo de agrupaciones PUC (`agrupaciones.py`)
aplicado al panel mensual del histórico (a 6 dígitos). Del reporte de cuentas
principales solo se usa ASOCIADOS y los metadatos de identificación.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

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

# ── Pestaña Sector ────────────────────────────────────────────────────────────
# Métricas seleccionables → (columna en la foto enriquecida, ¿es monto en COP?).
# "Número de entidades" se calcula contando filas (columna especial __count__).
METRICAS_SECTOR = {
    "Activo": ("100000", True),
    "Pasivo": ("200000", True),
    "Patrimonio": ("300000", True),
    "Cartera bruta": ("CARTERA_BRUTA", True),
    "Depósitos": ("210000", True),
    "Aportes": ("APORTES_SOCIALES_ASOCIADOS", True),
    "Número de asociados": ("ASOCIADOS", False),
    "Número de entidades": ("__count__", False),
}
ORDEN_CATEGORIAS = ["Plena", "Intermedia", "Básica"]


def _agrega_metrica(df, grupo_col, metrica):
    """Suma (o cuenta) la métrica por grupo; devuelve una Serie indexada por grupo."""
    col, _ = METRICAS_SECTOR[metrica]
    g = df.groupby(grupo_col, observed=True)
    return g.size() if col == "__count__" else g[col].sum()


_MESES = {"03": "mar", "06": "jun", "09": "sep", "12": "dic"}


def _etiqueta_periodo(periodo):
    """'2024-12' → '2024'; cortes intermedios → '2026·mar' (para el eje de barras)."""
    anio, mes = periodo.split("-")
    return anio if mes == "12" else f"{anio}·{_MESES.get(mes, mes)}"


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
    # Agrupaciones por entidad (Cartera bruta y Aportes) para la pestaña Sector
    agr = an.agrupaciones_entidad(h, corte, ["CARTERA_BRUTA", "APORTES_SOCIALES_ASOCIADOS"])
    foto = foto.merge(agr, on="CODIGO ENTIDAD", how="left")
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
        # las entidades disponibles dependen de los filtros anteriores
        base_ent = foto
        if sel_dep:
            base_ent = base_ent[base_ent["DEPARTAMENTO"].isin(sel_dep)]
        if sel_mun:
            base_ent = base_ent[base_ent["MUNICIPIO"].isin(sel_mun)]
        if sel_cat:
            base_ent = base_ent[base_ent["CATEGORIA"].isin(sel_cat)]
        if sel_sub:
            base_ent = base_ent[base_ent["SUBCATEGORIA"].isin(sel_sub)]
        ents = sorted(base_ent["ENTIDAD"].dropna().unique())
        sel_ent = st.multiselect("Entidad", ents, default=[])

    f = foto
    if sel_dep:
        f = f[f["DEPARTAMENTO"].isin(sel_dep)]
    if sel_mun:
        f = f[f["MUNICIPIO"].isin(sel_mun)]
    if sel_cat:
        f = f[f["CATEGORIA"].isin(sel_cat)]
    if sel_sub:
        f = f[f["SUBCATEGORIA"].isin(sel_sub)]
    if sel_ent:
        f = f[f["ENTIDAD"].isin(sel_ent)]
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

    tabs = st.tabs(["Principales cifras", "Sector", "Balance", "Cartera",
                    "Depósitos y fondeo", "Rentabilidad", "Glosario"])

    # ── TAB 1 · Principales cifras ──────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Estructura Financiera")
        st.caption("Cifras Financieras Expresadas en Millones de Pesos Colombianos")

        def _mill(v):  # monto en millones de pesos, con separador de miles
            return "—" if v is None or v != v else f"{v / 1e6:,.0f}"

        def _pctv(v):  # variación porcentual con signo
            return "—" if v is None or v != v else f"{v:+.1f}%"

        tot_a = f["100000"].sum()
        tot_p = f["200000"].sum()
        tot_pt = f["300000"].sum()
        m = st.columns(5)
        m[0].metric("Activo", _mill(tot_a))
        m[1].metric("Pasivo", _mill(tot_p))
        m[2].metric("Patrimonio", _mill(tot_pt))
        m[3].metric("Pasivo / Activo", pct(tot_p / tot_a * 100) if tot_a else "—")
        m[4].metric("Patrimonio / Activo", pct(tot_pt / tot_a * 100) if tot_a else "—")

        bal = serie[["100000", "200000", "300000"]].rename(
            columns={"100000": "Activo", "200000": "Pasivo", "300000": "Patrimonio"})
        bal["Pasivo/Activo"] = (bal["Pasivo"] / bal["Activo"] * 100).where(bal["Activo"] != 0)
        bal["Patrimonio/Activo"] = (bal["Patrimonio"] / bal["Activo"] * 100).where(bal["Activo"] != 0)
        RUBROS = ["Activo", "Pasivo", "Patrimonio"]
        RATIOS = ["Pasivo/Activo", "Patrimonio/Activo"]
        SEQ = [C_ACT, C_PAT, C_DEP]

        # ── Línea de tiempo compartida + dos gráficas lado a lado ───────────────
        trims = [p for p in bal.index if p[-2:] in ("03", "06", "09", "12")]
        ini, fin = st.select_slider("Línea de tiempo", options=trims,
                                    value=(trims[0], trims[-1]))
        vis = [p for p in trims if ini <= p <= fin]

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Evolución trimestral** (millones COP)")
            trim = (bal.loc[vis, RUBROS] / 1e6).reset_index()
            largo = trim.melt(id_vars="PERIODO", value_vars=RUBROS,
                              var_name="Rubro", value_name="VALOR")
            fig = px.line(largo, x="PERIODO", y="VALOR", color="Rubro",
                          color_discrete_sequence=SEQ,
                          labels={"PERIODO": "", "VALOR": "Saldo (millones COP)"})
            # Gráfica normal: al señalar un punto se muestra el valor de ese mes.
            fig.update_traces(hovertemplate="%{fullData.name}: %{y:,.0f}<extra></extra>")
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                              hovermode="closest",
                              legend=dict(orientation="h", y=-0.18))
            st.plotly_chart(fig, width="stretch")
        with g2:
            st.markdown("**Estructura relativa** (% del activo)")
            rel = bal.loc[vis, RATIOS].reset_index()
            largo2 = rel.melt(id_vars="PERIODO", value_vars=RATIOS,
                              var_name="Indicador", value_name="VALOR")
            fig2 = px.line(largo2, x="PERIODO", y="VALOR", color="Indicador",
                           color_discrete_sequence=[C_PAT, C_DEP],
                           labels={"PERIODO": "", "VALOR": "% del activo"})
            fig2.update_traces(hovertemplate="%{fullData.name}: %{y:.1f}%<extra></extra>")
            fig2.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0),
                               hovermode="closest",
                               legend=dict(orientation="h", y=-0.18))
            st.plotly_chart(fig2, width="stretch")

        # ── Variaciones (tabla resumen) ─────────────────────────────────────────
        st.markdown("**Variaciones**")
        last = bal.index[-1]
        anio = int(last[:4])
        base_12m = f"{anio - 1}-{last[5:]}"      # mismo mes del año anterior
        base_ytd = f"{anio - 1}-12"              # último cierre anual

        def _var(col, base):
            if base in bal.index and bal.at[base, col]:
                return (bal.at[last, col] / bal.at[base, col] - 1) * 100
            return float("nan")

        resumen = pd.DataFrame({
            "Saldo (millones)": {r: _mill(bal.at[last, r]) for r in RUBROS},
            "Var. anual (12 m)": {r: _pctv(_var(r, base_12m)) for r in RUBROS},
            "Año corrido (vs. último cierre)": {r: _pctv(_var(r, base_ytd)) for r in RUBROS},
        })
        st.table(resumen)
        st.caption(f"Variación anual: corte **{last}** frente a **{base_12m}** · "
                   f"Año corrido: frente al último cierre anual **{base_ytd}**.")

        # ── Crecimiento anual histórico por rubro ───────────────────────────────
        st.markdown("**Crecimiento anual histórico** (% de variación entre cierres de diciembre)")
        cierres = sorted(p for p in bal.index if p.endswith("-12"))
        filas = {}
        for prev, cur in zip(cierres, cierres[1:]):
            filas[cur[:4]] = {r: _pctv((bal.at[cur, r] / bal.at[prev, r] - 1) * 100)
                              if bal.at[prev, r] else "—" for r in RUBROS}
        if not last.endswith("-12") and base_ytd in bal.index:
            filas[f"{_etiqueta_periodo(last)} (corrido)"] = {
                r: _pctv(_var(r, base_ytd)) for r in RUBROS}
        if filas:
            st.table(pd.DataFrame(filas).T[RUBROS])

    # ── TAB 2 · Sector ──────────────────────────────────────────────────────────
    with tabs[1]:
        opciones = list(METRICAS_SECTOR.keys())
        cs = st.columns(2)
        m1 = cs[0].selectbox("Métrica 1", opciones, index=opciones.index("Activo"))
        m2 = cs[1].selectbox("Métrica 2 (opcional)", ["— Ninguno —"] + opciones, index=0)
        m2 = None if m2 == "— Ninguno —" else m2

        # Montos en miles de millones (÷1e9); asociados en miles (÷1e3);
        # nº de entidades sin escalar. Las unidades se aclaran en el caption.
        def _monto(metrica):
            return METRICAS_SECTOR[metrica][1]

        def _escala_div(metrica):
            if _monto(metrica):
                return 1e9
            return 1e3 if metrica == "Número de asociados" else 1

        def _esc(metrica, valores):  # escala los valores según la métrica
            d = _escala_div(metrica)
            return [v / d for v in valores]

        def _txt(metrica, valores):  # etiquetas de las barras
            d = _escala_div(metrica)
            return ([f"{v / d:,.0f}" for v in valores] if d != 1
                    else [cantidad(v) for v in valores])

        # Asignación de ejes POR TIPO de métrica: las cifras financieras comparten
        # escala (mM) y van al eje principal; los conteos (asociados/entidades) van
        # al eje secundario. Si solo se eligen conteos, el 1º ocupa el principal.
        metricas_sel = [m for m in (m1, m2) if m]
        if any(_monto(m) for m in metricas_sel):
            secundarias = {m for m in metricas_sel if not _monto(m)}
        else:
            secundarias = set(metricas_sel[1:])

        def _sec(metrica):
            return metrica in secundarias

        def _titulo_eje(secundario):  # título según las métricas de ese eje
            metr = [m for m in metricas_sel if _sec(m) == secundario]
            if not metr:
                return ""
            return "mM COP" if any(_monto(m) for m in metr) else metr[0]

        st.caption("Cifras financieras expresadas en miles de millones de pesos "
                   "colombianos · Cifra de asociados en miles")

        # ── Gráficos lado a lado: por categoría | por departamento ──────────────
        cg = st.columns(2)

        # Gráfico 1 · por categoría regulatoria (Plena → Intermedia → Básica)
        with cg[0]:
            st.subheader("Por categoría regulatoria")
            cats = [c for c in ORDEN_CATEGORIAS if c in f["CATEGORIA"].dropna().unique()]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            for i, (m, color) in enumerate([(m1, C_ACT), (m2, C_PAT)]):
                if not m:
                    continue
                s = _agrega_metrica(f, "CATEGORIA", m)
                y = [float(s.get(c, 0)) for c in cats]
                fig.add_trace(go.Bar(x=cats, y=_esc(m, y), name=m, marker_color=color,
                                     offsetgroup=i, alignmentgroup="g",
                                     text=_txt(m, y), textposition="outside"),
                              secondary_y=_sec(m))
            fig.update_yaxes(title_text=_titulo_eje(False), tickformat=",.0f", secondary_y=False)
            if secundarias:
                fig.update_yaxes(title_text=_titulo_eje(True), tickformat=",.0f", secondary_y=True)
            fig.update_layout(barmode="group", height=480, margin=dict(l=0, r=0, t=20, b=0),
                              legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig, width="stretch")

        # Gráfico 2 · por departamento (todos; se desliza dentro del contenedor)
        with cg[1]:
            st.subheader("Por departamento")
            deps = (_agrega_metrica(f, "DEPARTAMENTO", m1)
                    .sort_values(ascending=False).index.tolist()[::-1])  # mayor arriba
            figd = go.Figure()
            # La traza que se agrega de última queda ARRIBA en cada grupo: por eso
            # la 2ª (azul) va primero (debajo) y la 1ª (naranja) después.
            # Los valores van DENTRO de la barra (auto); los ejes X no muestran ticks.
            usa_sec = False
            for i, (m, color) in [(0, (m2, C_PAT)), (1, (m1, C_ACT))]:
                if not m:
                    continue
                s = _agrega_metrica(f, "DEPARTAMENTO", m)
                x = [float(s.get(d, 0)) for d in deps]
                eje = "x2" if _sec(m) else "x"
                usa_sec = usa_sec or eje == "x2"
                figd.add_trace(go.Bar(y=deps, x=_esc(m, x), orientation="h", name=m,
                                      marker_color=color, offsetgroup=i, alignmentgroup="g",
                                      text=[f"<b>{t}</b>" for t in _txt(m, x)],
                                      textposition="auto", insidetextanchor="start",
                                      textangle=0, textfont=dict(size=14), xaxis=eje))
            figd.update_layout(xaxis=dict(showticklabels=False, showgrid=False))
            if usa_sec:
                figd.update_layout(xaxis2=dict(overlaying="x", side="top",
                                               showticklabels=False, showgrid=False))
            alto = max(440, 58 * len(deps))  # ≈58 px/depto → barras amplias + scroll
            figd.update_layout(barmode="group", bargap=0.08, bargroupgap=0,
                               showlegend=False, height=alto,
                               margin=dict(l=0, r=20, t=10, b=0))
            with st.container(height=480):
                st.plotly_chart(figd, width="stretch")

        # ── Tabla · ranking de entidades ───────────────────────────────────────
        st.subheader("Entidades")
        tc = st.columns([2, 3])
        subs = sorted(f["SUBCATEGORIA"].dropna().unique())
        ver = tc[0].selectbox("Ver", ["Todas"] + subs)
        orden = tc[1].radio("Ordenar por", ["Activos", "Número de asociados"],
                            horizontal=True)
        col_ord = "100000" if orden == "Activos" else "ASOCIADOS"
        t = f if ver == "Todas" else f[f["SUBCATEGORIA"] == ver]
        t = t.sort_values(col_ord, ascending=False).reset_index(drop=True)
        tabla = t[["ENTIDAD", "SIGLA", "ASOCIADOS", "100000"]].copy()
        tabla.insert(0, "#", range(1, len(tabla) + 1))
        tabla["ASOCIADOS"] = tabla["ASOCIADOS"].map(miles)
        tabla["100000"] = tabla["100000"].map(pesos)
        tabla = tabla.rename(columns={"ENTIDAD": "Entidad", "SIGLA": "Sigla",
                                      "ASOCIADOS": "Asociados", "100000": "Activos"})
        st.dataframe(tabla, width="stretch", hide_index=True)

    # ── TAB 3 · Balance ─────────────────────────────────────────────────────────
    with tabs[2]:
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

    # ── TAB 4 · Cartera ─────────────────────────────────────────────────────────
    with tabs[3]:
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

    # ── TAB 5 · Depósitos y fondeo ──────────────────────────────────────────────
    with tabs[4]:
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

    # ── TAB 6 · Rentabilidad ────────────────────────────────────────────────────
    with tabs[5]:
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

    # ── TAB 7 · Glosario ────────────────────────────────────────────────────────
    with tabs[6]:
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
