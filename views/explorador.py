"""Explorador — ficha financiera detallada por entidad."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from config import CATALOGO_CUENTAS
from src import analytics as an
from src import data
from src.format import miles, pesos, pesos_full, pct

# Indicadores a mostrar con su etiqueta y formato
INDICADORES = [
    ("ROA", "ROA del periodo", "Excedente / Activo"),
    ("ROE", "ROE del periodo", "Excedente / Patrimonio"),
    ("SOLVENCIA", "Solvencia", "Patrimonio / Activo"),
    ("ENDEUDAMIENTO", "Endeudamiento", "Pasivo / Activo"),
    ("CARTERA_ACTIVO", "Cartera / Activo", "Cartera / Activo"),
    ("FONDEO_DEPOSITOS", "Fondeo por depósitos", "Depósitos / Activo"),
    ("MARGEN_EXCEDENTE", "Margen de excedente", "Excedente / Ingresos"),
    ("EFICIENCIA", "Carga administrativa", "Gastos admón. / Ingresos"),
]

# Indicadores calculados con el plan de cuentas a 6 dígitos (catálogo de
# agrupaciones portado de analisis_tasas). Aplican sobre todo a entidades
# con actividad de crédito; en las demás salen vacíos.
INDICADORES_6DIG = [
    ("CALIDAD_RIESGO", "Calidad por riesgo", "Cartera en riesgo (B-E) / cartera total"),
    ("CARTERA_PRODUCTIVA", "Cartera productiva (A+B)", "Cartera en categorías A y B / cartera bruta"),
    ("COBERTURA_RIESGO", "Cobertura por riesgo", "Provisiones totales / cartera en riesgo"),
    ("COBERTURA_GENERAL", "Cobertura general", "Provisiones (capital + general) / cartera bruta"),
    ("FONDEO_DEP_CARTERA", "Fondeo depósitos / cartera", "Depósitos sin intereses / cartera bruta"),
    ("FONDEO_APORTES", "Fondeo aportes / cartera", "Aportes sociales netos / cartera bruta"),
    ("CAPITAL_INSTITUCIONAL", "Capital institucional", "Reservas, fondos y donaciones / activo"),
    ("ACTIVOS_IMPRODUCTIVOS", "Activos improductivos", "Activos que no generan rendimiento / activo"),
    ("EFICIENCIA_OPERATIVA", "Eficiencia operativa", "(Gastos admón. + costos financieros) / (ingresos de cartera + recuperaciones)"),
    ("MARGEN_FINANCIERO", "Margen financiero", "(Ingresos de cartera − costos financieros) / ingresos de cartera"),
    ("MARGEN_OPERACIONAL", "Margen operacional", "(Ing. cartera + recuperaciones − costos − admón.) / ingresos de cartera"),
    ("DIVERSIFICACION", "Diversificación de ingresos", "Ingresos no financieros / ingresos totales"),
]

MODALIDADES = [
    ("PCT_VIVIENDA", "Vivienda"), ("PCT_CONSUMO", "Consumo"),
    ("PCT_MICROCREDITO", "Microcrédito"), ("PCT_COMERCIAL", "Comercial"),
    ("PCT_PRODUCTIVO", "Productivo y otros"),
]


def render():
    st.header("🔍 Explorador de entidades")
    df = an.agregar_indicadores(data.entidades())
    df = an.agregar_indicadores_6dig(df, data.saldos_6dig())

    nombres = df["ENTIDAD"] + "  (" + df["SIGLA"].fillna("") + ")"
    idx = st.selectbox("Selecciona una entidad", range(len(df)),
                       format_func=lambda i: nombres.iloc[i])
    e = df.iloc[idx]

    st.subheader(e["ENTIDAD"])
    meta = st.columns(4)
    meta[0].markdown(f"**NIT**\n\n{e['NIT']}")
    meta[1].markdown(f"**Tipo**\n\n{e['TIPO ENTIDAD']}")
    meta[2].markdown(f"**Ubicación**\n\n{e['MUNICIPIO']}, {e['DEPARTAMENTO']}")
    meta[3].markdown(f"**Nivel supervisión**\n\n{e['NIVEL DE SUPERVISION']}")
    meta = st.columns(4)
    meta[0].metric("Asociados", miles(e["ASOCIADOS"]))
    meta[1].metric("Empleados", miles(e["EMPLEADOS"]))
    meta[2].markdown(f"**Representante legal**\n\n{e['REPRESENTANTE LEGAL']}")
    meta[3].markdown(f"**Actividad**\n\n{e.get('ACTIVIDAD ECONOMICA', '')}")

    st.divider()

    # ── Cifras y estructura ────────────────────────────────────────────────────
    k = st.columns(4)
    k[0].metric("Activos", pesos(e["100000"]))
    k[1].metric("Pasivos", pesos(e["200000"]))
    k[2].metric("Patrimonio", pesos(e["300000"]))
    k[3].metric("Excedentes", pesos(e["350000"]))

    # ── Indicadores vs. mediana del sector (mismo tipo) ────────────────────────
    st.subheader("Indicadores financieros")
    pares = df[df["TIPO ENTIDAD"] == e["TIPO ENTIDAD"]]
    cols = st.columns(4)
    for i, (code, label, _) in enumerate(INDICADORES):
        val = e[code]
        med = pares[code].median()
        delta = (val - med) if val == val and med == med else None
        cols[i % 4].metric(
            label, pct(val),
            delta=(f"{delta:+.1f} pp vs. mediana" if delta is not None else None),
            help=f"{dict((c, h) for c, _, h in INDICADORES)[code]} · "
                 f"Mediana del tipo: {pct(med)}",
        )

    st.divider()

    # ── Indicadores de cartera y gestión (cuentas a 6 dígitos) ─────────────────
    st.subheader("Cartera y gestión (detalle a 6 dígitos)")
    if e[[c for c, _, _ in INDICADORES_6DIG]].notna().any():
        ayuda = dict((c, h) for c, _, h in INDICADORES_6DIG)
        cols = st.columns(4)
        for i, (code, label, _) in enumerate(INDICADORES_6DIG):
            val = e[code]
            med = pares[code].median()
            delta = (val - med) if val == val and med == med else None
            cols[i % 4].metric(
                label, pct(val),
                delta=(f"{delta:+.1f} pp vs. mediana" if delta is not None else None),
                help=f"{ayuda[code]} · Mediana del tipo: {pct(med)}",
            )

        # Mezcla de cartera por modalidad
        mezcla = [{"Modalidad": nom, "Participación": float(e[c])}
                  for c, nom in MODALIDADES if e[c] == e[c] and e[c] > 0]
        if mezcla:
            st.subheader("Mezcla de cartera por modalidad")
            fig = px.pie(mezcla, names="Modalidad", values="Participación", hole=0.45,
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=320, margin=dict(t=10, b=10), showlegend=False)
            st.plotly_chart(fig, width="stretch")
    else:
        st.caption("Esta entidad no reporta cuentas de cartera a 6 dígitos.")

    st.divider()

    # ── Composición de balance ─────────────────────────────────────────────────
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Composición del activo")
        _torta(e, ["110000", "120000", "140000", "160000", "170000", "190000"])
    with g2:
        st.subheader("Pasivo + Patrimonio")
        _torta(e, ["210000", "230000", "240000", "260000", "270000", "300000"])

    # ── Estado de resultados resumido ──────────────────────────────────────────
    st.subheader("Estado de resultados (resumen)")
    er = []
    for code in ["400000", "500000", "510000", "520000", "600000", "350000"]:
        if code in df.columns:
            er.append({"Cuenta": f"{code} · {CATALOGO_CUENTAS[code].title()}",
                       "Valor": pesos_full(e[code])})
    st.dataframe(er, width="stretch", hide_index=True)


def _torta(e, codes):
    datos = [{"Cuenta": CATALOGO_CUENTAS[c].title(), "Valor": float(e[c])}
             for c in codes if c in e.index and float(e[c]) > 0]
    if not datos:
        st.caption("Sin datos para graficar.")
        return
    fig = px.pie(datos, names="Cuenta", values="Valor", hole=0.45,
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_traces(textposition="inside", textinfo="percent")
    fig.update_layout(height=340, margin=dict(t=10, b=10), legend_font_size=11)
    st.plotly_chart(fig, width="stretch")
