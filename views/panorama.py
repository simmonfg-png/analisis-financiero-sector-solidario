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

# Nombres de mes en español (Plotly de Streamlit no trae el locale es).
_MES_LARGO = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo",
              6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre",
              10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
_MES_CORTO = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "Mayo", 6: "Jun",
              7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}


def _mes_largo(periodo):
    """'2022-12' → 'Diciembre 2022' (encabezado del tooltip)."""
    return f"{_MES_LARGO[int(periodo[5:])]} {periodo[:4]}"


def _mes_corto(periodo):
    """'2022-12' → 'Dic 2022' (etiqueta del eje)."""
    return f"{_MES_CORTO[int(periodo[5:])]} {periodo[:4]}"


def _eje_meses(fig, periodos):
    """Eje X en español: la categoría es el nombre completo del mes (lo que
    muestra el encabezado del tooltip). El eje solo rotula AÑOS, dibujados como
    anotaciones (no con ticktext, que contaminaría el tooltip en enero)."""
    xl = [_mes_largo(p) for p in periodos]
    vistos, anota = set(), []
    for p in periodos:
        if p[:4] not in vistos:
            vistos.add(p[:4])
            anota.append(dict(x=_mes_largo(p), y=0, xref="x", yref="paper",
                              yanchor="top", yshift=-6, showarrow=False,
                              text=p[:4], font=dict(size=11, color="#555")))
    fig.update_xaxes(categoryorder="array", categoryarray=xl,
                     showticklabels=False, showspikes=True, spikemode="across",
                     spikethickness=1, spikecolor="#888", spikedash="solid",
                     spikesnap="cursor")
    fig.update_layout(annotations=anota)


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

        # Formato colombiano: $ + punto para miles + coma para decimales.
        def _mill(v):  # monto en millones de pesos
            if v is None or v != v:
                return "—"
            return "$" + f"{v / 1e6:,.0f}".replace(",", ".")

        def _pctv(v):  # variación porcentual con signo
            return "—" if v is None or v != v else f"{v:+.1f}%".replace(".", ",")

        def _pct_co(v):  # porcentaje sin signo
            return "—" if v is None or v != v else f"{v:.1f}%".replace(".", ",")

        tot_a = f["100000"].sum()
        tot_p = f["200000"].sum()
        tot_pt = f["300000"].sum()
        m = st.columns(5)
        m[0].metric("Activo", _mill(tot_a))
        m[1].metric("Pasivo", _mill(tot_p))
        m[2].metric("Patrimonio", _mill(tot_pt))
        m[3].metric("Pasivo / Activo", _pct_co(tot_p / tot_a * 100) if tot_a else "—")
        m[4].metric("Patrimonio / Activo", _pct_co(tot_pt / tot_a * 100) if tot_a else "—")

        bal = serie[["100000", "200000", "300000"]].rename(
            columns={"100000": "Activo", "200000": "Pasivo", "300000": "Patrimonio"})
        bal["Pasivo/Activo"] = (bal["Pasivo"] / bal["Activo"] * 100).where(bal["Activo"] != 0)
        bal["Patrimonio/Activo"] = (bal["Patrimonio"] / bal["Activo"] * 100).where(bal["Activo"] != 0)
        RUBROS = ["Activo", "Pasivo", "Patrimonio"]
        RATIOS = ["Pasivo/Activo", "Patrimonio/Activo"]
        SEQ = [C_ACT, C_PAT, C_DEP]

        # ── Línea de tiempo compartida + dos gráficas lado a lado ───────────────
        meses = list(bal.index)  # todos los meses del histórico
        ini, fin = st.select_slider(
            "Línea de tiempo", options=meses, value=(meses[0], meses[-1]),
            format_func=_mes_corto)
        vis = [p for p in meses if ini <= p <= fin]


        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Evolución mensual** (millones COP)")
            trim = (bal.loc[vis, RUBROS] / 1e6).reset_index()
            trim["Mes"] = trim["PERIODO"].map(_mes_largo)
            largo = trim.melt(id_vars=["PERIODO", "Mes"], value_vars=RUBROS,
                              var_name="Rubro", value_name="VALOR")
            fig = px.line(largo, x="Mes", y="VALOR", color="Rubro",
                          color_discrete_sequence=SEQ,
                          labels={"Mes": "", "VALOR": "Saldo (millones COP)"})
            # Tooltip unificado: marcador de color + nombre del rubro + valor del mes.
            # separators=",." → formato colombiano (coma decimal, punto de miles).
            fig.update_traces(hovertemplate="%{fullData.name}: $%{y:,.0f}<extra></extra>")
            _eje_meses(fig, vis)
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=28),
                              hovermode="x unified", separators=",.",
                              legend=dict(orientation="h", y=-0.18))
            st.plotly_chart(fig, width="stretch")
        with g2:
            st.markdown("**Estructura relativa** (% del activo)")
            rel = bal.loc[vis, RATIOS].reset_index()
            rel["Mes"] = rel["PERIODO"].map(_mes_largo)
            largo2 = rel.melt(id_vars=["PERIODO", "Mes"], value_vars=RATIOS,
                              var_name="Indicador", value_name="VALOR")
            fig2 = px.line(largo2, x="Mes", y="VALOR", color="Indicador",
                           color_discrete_sequence=[C_PAT, C_DEP],
                           labels={"Mes": "", "VALOR": "% del activo"})
            fig2.update_traces(hovertemplate="%{fullData.name}: %{y:.1f} %<extra></extra>")
            _eje_meses(fig2, vis)
            fig2.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=28),
                               hovermode="x unified", separators=",.",
                               legend=dict(orientation="h", y=-0.18))
            st.plotly_chart(fig2, width="stretch")

        # ── Actividad Financiera (cartera, depósitos, capital, excedentes) ──────
        st.divider()
        st.subheader("Actividad Financiera")
        st.caption("Cifras Financieras Expresadas en Millones de Pesos Colombianos")

        def _num(v):  # conteo con separador de miles colombiano (punto)
            return "—" if v is None or v != v else f"{v:,.0f}".replace(",", ".")

        mc = st.columns(5)
        mc[0].metric("Cartera bruta", _mill(va("CARTERA_BRUTA")))
        mc[1].metric("Depósitos", _mill(f["210000"].sum()))
        mc[2].metric("Capital social", _mill(va("CAPITAL_SOCIAL")))
        mc[3].metric("Excedentes", _mill(f["350000"].sum()))
        mc[4].metric("Base social (asociados)", _num(f["ASOCIADOS"].sum()))

        # Serie de asociados: hoy solo el dato del corte; al cargar el histórico
        # (parquet PERIODO·CODIGO ENTIDAD·ASOCIADOS) la serie se llena sola.
        if data.historico_asociados_disponible():
            ha = data.historico_asociados()
            if filtrado:
                ha = ha[ha["CODIGO ENTIDAD"].isin(f["CODIGO ENTIDAD"])]
            aso = ha.groupby("PERIODO")["ASOCIADOS"].sum()
            aso.index = aso.index.astype(str)
            aso = aso[aso.index <= corte].sort_index()
        else:
            aso = pd.Series({corte: float(f["ASOCIADOS"].sum())})

        # Series mensuales: cartera y capital desde las agrupaciones; depósitos y
        # excedentes desde las cuentas 210000 y 350000 del histórico.
        finser = pd.DataFrame({
            "Cartera bruta": an.serie_alias(panel, "CARTERA_BRUTA"),
            "Depósitos": serie["210000"],
            "Capital social": an.serie_alias(panel, "CAPITAL_SOCIAL"),
        })
        FIN = ["Cartera bruta", "Depósitos", "Capital social"]

        # Línea de tiempo propia de esta sección (independiente de la de arriba).
        ini2, fin2 = st.select_slider("Línea de tiempo", options=meses,
                                      value=(meses[0], meses[-1]),
                                      format_func=_mes_corto, key="lt_actividad")
        vis2 = [p for p in meses if ini2 <= p <= fin2]

        h1, h2 = st.columns(2)
        with h1:
            st.markdown("**Cifras financieras** (millones COP)")
            d = (finser.loc[vis2, FIN] / 1e6).reset_index()
            d["Mes"] = d["PERIODO"].map(_mes_largo)
            largo3 = d.melt(id_vars=["PERIODO", "Mes"], value_vars=FIN,
                            var_name="Concepto", value_name="VALOR")
            figf = px.line(largo3, x="Mes", y="VALOR", color="Concepto",
                           color_discrete_sequence=[C_CAR, C_DEP, C_ACT],
                           labels={"Mes": "", "VALOR": "Saldo (millones COP)"})
            figf.update_traces(hovertemplate="%{fullData.name}: $%{y:,.0f}<extra></extra>")
            _eje_meses(figf, vis2)
            figf.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=28),
                               hovermode="x unified", separators=",.",
                               legend=dict(orientation="h", y=-0.18))
            st.plotly_chart(figf, width="stretch")
        with h2:
            st.markdown("**Base social** (número de asociados)")
            da = aso[aso.index.isin(vis2)].reset_index()
            da.columns = ["PERIODO", "Asociados"]
            da["Mes"] = da["PERIODO"].map(_mes_largo)
            figa = px.line(da, x="Mes", y="Asociados", markers=True,
                           color_discrete_sequence=[C_PAT],
                           labels={"Mes": "", "Asociados": ""})
            figa.update_traces(hovertemplate="Asociados: %{y:,.0f}<extra></extra>")
            _eje_meses(figa, list(da["PERIODO"]))
            figa.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=28),
                               hovermode="x unified", separators=",.",
                               legend=dict(orientation="h", y=-0.18))
            st.plotly_chart(figa, width="stretch")
            if len(aso) <= 1:
                st.caption(f"Por ahora solo está disponible el dato del corte "
                           f"(**{_mes_largo(corte)}**). El histórico de asociados "
                           "se añadirá cuando se cargue.")

        # ── Crecimiento anual histórico (al final, todos los rubros) ─────────────
        st.divider()
        st.markdown("**Crecimiento anual histórico** "
                    "(% de variación entre cierres de diciembre)")
        tser = pd.DataFrame({
            "Activo": bal["Activo"], "Pasivo": bal["Pasivo"], "Patrimonio": bal["Patrimonio"],
            "Cartera bruta": finser["Cartera bruta"], "Depósitos": finser["Depósitos"],
            "Capital social": finser["Capital social"], "Excedentes": serie["350000"],
            "Base social": aso.reindex(bal.index),
        })
        COLS = ["Activo", "Pasivo", "Patrimonio", "Cartera bruta", "Depósitos",
                "Capital social", "Excedentes", "Base social"]
        last = bal.index[-1]
        base_ytd = f"{int(last[:4]) - 1}-12"     # último cierre anual
        cierres = sorted(p for p in tser.index if p.endswith("-12"))

        def _crec(col, prev, cur):
            a, b = tser.at[prev, col], tser.at[cur, col]
            if pd.isna(a) or pd.isna(b) or a == 0:
                return float("nan")
            return (b / a - 1) * 100

        filas = {}
        for prev, cur in zip(cierres, cierres[1:]):
            filas[cur[:4]] = {c: _crec(c, prev, cur) for c in COLS}
        if not last.endswith("-12") and base_ytd in tser.index:
            # Año en curso (sin cerrar). Los saldos se comparan contra el último
            # cierre de diciembre (lo corrido del año); los Excedentes —un flujo
            # que se acumula mes a mes— contra el mismo mes del año anterior.
            base_12m = f"{int(last[:4]) - 1}-{last[5:]}"
            filas[last[:4]] = {
                c: _crec(c, base_12m if c == "Excedentes" else base_ytd, last)
                for c in COLS}
        if filas:
            num = pd.DataFrame(filas).T[COLS].astype(float)

            # Mapa de calor: degradado por celda centrado en 0 (rojo = caída,
            # verde = crecimiento; intensidad según la magnitud). Escala global.
            _mx = num.abs().max().max()      # máximo en valor absoluto (ignora NaN)
            escala = float(_mx) if pd.notna(_mx) and _mx else 1.0

            def _color(v):
                if pd.isna(v) or escala == 0:
                    return ""
                t = max(-1.0, min(1.0, v / escala))
                # gamma<1 realza las magnitudes pequeñas (si no, el outlier
                # deja casi sin color a los crecimientos típicos de ~10%).
                t = abs(t) ** 0.6 * (1 if t >= 0 else -1)
                if t >= 0:  # blanco → verde
                    r, g, b = int(255 - t * 179), int(255 - t * 80), int(255 - t * 175)
                else:       # blanco → rojo
                    s = -t
                    r, g, b = int(255 - s * 26), int(255 - s * 198), int(255 - s * 202)
                return f"background-color: rgb({r},{g},{b})"

            sty = (num.style
                   .map(_color)
                   .format(lambda v: _pctv(v) if pd.notna(v) else "—"))
            st.table(sty)
            st.caption(
                f"Cada porcentaje indica cuánto **creció o se redujo** el rubro en "
                f"un año: compara el cierre de diciembre con el de diciembre "
                f"anterior. La fila **{last[:4]}** es el año en curso (aún sin "
                f"cerrar): los saldos se comparan con el último cierre de diciembre "
                f"(lo que va **corrido** del año) y los **Excedentes**, por ser un "
                f"resultado que se acumula mes a mes, con el **mismo mes del año "
                f"anterior**.")

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
        st.subheader("Cartera de Crédito")
        st.caption("Cifras Financieras Expresadas en Millones de Pesos Colombianos")

        # Formato colombiano: $ + punto para miles, sobre la cifra en millones.
        def _mill(v):
            if v is None or v != v:
                return "—"
            return "$" + f"{v / 1e6:,.0f}".replace(",", ".")

        # Cartera bruta total: centrada, grande y en negrita.
        cb = va("CARTERA_BRUTA")
        st.markdown(
            f"<div style='text-align:center;margin:0.4rem 0 1.2rem'>"
            f"<div style='font-size:1rem;color:#666;letter-spacing:.02em'>Cartera Bruta</div>"
            f"<div style='font-size:2.9rem;font-weight:800;color:{C_CAR};line-height:1.1'>"
            f"{_mill(cb)}</div></div>",
            unsafe_allow_html=True,
        )

        # Peso de cada modalidad sobre el total: torta + tabla en millones COP.
        datos = [{"Modalidad": etq, "Valor": va(a)} for a, etq in MODALIDADES]
        datos = [d for d in datos if d["Valor"] and d["Valor"] > 0]
        g1, g2 = st.columns([1, 1])
        with g1:
            fig = px.pie(datos, names="Modalidad", values="Valor", hole=0.45,
                         color_discrete_sequence=PALETA)
            fig.update_traces(textposition="inside", textinfo="percent",
                              hovertemplate="%{label}: %{percent}<extra></extra>")
            fig.update_layout(height=360, margin=dict(t=10, b=0), legend_font_size=11,
                              separators=",.")
            st.plotly_chart(fig, width="stretch")
        with g2:
            tdf = pd.DataFrame(datos).sort_values("Valor", ascending=False)
            tabla = pd.DataFrame({
                "Valor (millones COP)": tdf["Valor"].map(_mill).values,
            }, index=tdf["Modalidad"].values)
            tabla.index.name = "Modalidad"
            st.table(tabla)

        # ── Calidad de Cartera ─────────────────────────────────────────────────
        st.divider()
        st.subheader("Calidad de Cartera")

        # Cartera en riesgo = capital en categorías B-E (CARTERA_RIESGO_CAPITAL).
        # Provisiones = individuales sobre capital + generales (sin interés/otros).
        ri = va("CARTERA_RIESGO_CAPITAL")
        pr = va("PROVISIONES_INDIVIDUALES_CAPITAL") + va("PROVISIONES_GENERALES")
        cast = va("CASTIGOS")
        cal_riesgo = ri / cb * 100 if cb else float("nan")
        cal_castigos = (ri + cast) / (cb + cast) * 100 if (cb + cast) else float("nan")
        cob_riesgo = pr / ri * 100 if ri else float("nan")
        # Indicadores de "altura de mora" pendientes: requieren el detalle de
        # cartera por días de vencimiento (raw_cartera), aún no integrado.
        def _pct2(v):  # porcentaje con dos decimales, coma decimal (es-CO)
            return "—" if v is None or v != v else f"{v:.2f}%".replace(".", ",")

        q = st.columns(3)
        q[0].metric("Calidad por riesgo", _pct2(cal_riesgo),
                    help="Cartera en riesgo (capital, categorías B-E) / cartera bruta")
        q[1].metric("Calidad con castigos", _pct2(cal_castigos),
                    help="(Cartera en riesgo + castigos) / (cartera bruta + castigos)")
        q[2].metric("Cobertura cartera en riesgo", _pct2(cob_riesgo),
                    help="Provisiones (individuales capital + generales) / cartera en riesgo")

        v = st.columns(3)
        v[0].metric("Cartera en riesgo ($)", _mill(ri),
                    help="Capital en categorías B a E (CARTERA_RIESGO_CAPITAL)")
        v[1].metric("Provisiones totales ($)", _mill(pr),
                    help="Provisiones individuales sobre capital + generales")

        st.subheader("Calidad y cobertura en el tiempo")
        calidad = an.ratio_alias(panel, "CARTERA_RIESGO_CAPITAL", "CARTERA_BRUTA")
        prov_ser = (an.serie_alias(panel, "PROVISIONES_INDIVIDUALES_CAPITAL")
                    + an.serie_alias(panel, "PROVISIONES_GENERALES"))
        riesgo_ser = an.serie_alias(panel, "CARTERA_RIESGO_CAPITAL")
        cobertura = (prov_ser / riesgo_ser * 100).where(riesgo_ser != 0)
        # Doble eje: calidad (~8%) a la izquierda, cobertura (~90%) a la derecha,
        # para que ambas series sean legibles pese a su escala distinta.
        per = list(calidad.index)
        xm = [_mes_largo(p) for p in per]  # eje en español (Enero 2020, …)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=xm, y=calidad.values, name="Calidad",
                                 mode="lines", line=dict(color=C_CAR, width=2),
                                 hovertemplate="%{fullData.name}: %{y:.2f} %<extra></extra>"),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=xm, y=cobertura.values, name="Cobertura",
                                 mode="lines", line=dict(color=C_DEP, width=2),
                                 hovertemplate="%{fullData.name}: %{y:.2f} %<extra></extra>"),
                      secondary_y=True)
        fig.update_yaxes(title_text="Calidad por riesgo (%)", color=C_CAR,
                         secondary_y=False, rangemode="normal")
        fig.update_yaxes(title_text="Cobertura por riesgo (%)", color=C_DEP,
                         secondary_y=True, rangemode="normal")
        _eje_meses(fig, per)
        fig.update_layout(height=330, margin=dict(l=0, r=0, t=10, b=28),
                          hovermode="x unified", separators=",.",
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
