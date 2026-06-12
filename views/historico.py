"""Histórico CAC — series mensuales 2018-2026 por entidad o sector."""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import analytics as an
from src import data
from src.format import GLOSARIO, pesos, pct

PALETA = px.colors.qualitative.Set2

# Cuentas sugeridas para graficar (las demás se pueden buscar en el catálogo)
CUENTAS_BASE = ["100000", "200000", "300000", "140000", "210000", "350000"]

SECTOR = "— Todo el sector CAC —"

# Novedades conocidas que explican saltos en las series (censo jun-2026;
# detalle en NOVEDADES COOPERATIVAS CAC 2018-2026.xlsx)
EVENTOS = {
    1190: [("2019-12", "Absorbe a INEM Kennedy (COPINKE)"),
           ("2020-12", "Incorpora a Cooservicios (Boyacá)"),
           ("2024-06", "Absorbe a Coolever"),
           ("2025-12", "Absorción de Coompartir en curso")],
    2783: [("2021-10", "Incorpora a Laboyana (COOLAC)")],
    2871: [("2021-03", "Incorpora a Coopesagua (La Guajira)")],
    1100: [("2022-02", "Absorbe a Coopexxonmobil")],
    1457: [("2023-06", "Absorbe a COMUDEM (U. de Medellín)")],
    124:  [("2025-12", "Entra como CAC especializada al absorber a Progressa")],
}
EVENTOS_SECTOR = [
    ("2025-12", "Transición de catálogo de cuentas (PUC 2026)"),
]

# La fuente trae dañadas las tildes/eñes en algunos nombres
ARREGLOS_NOMBRE = {"ANTIOQUE??A": "ANTIOQUEÑA", "CR??DITO": "CRÉDITO"}


def _limpiar(nombre: str) -> str:
    for malo, bueno in ARREGLOS_NOMBRE.items():
        nombre = nombre.replace(malo, bueno)
    return nombre.strip().title()


def render():
    st.header("📜 Histórico CAC")
    st.caption("Estados financieros mensuales de las cooperativas de ahorro y "
               "crédito · enero 2018 – abril 2026 · Supersolidaria")

    if not data.historico_disponible():
        st.warning("El histórico no está generado. Ejecuta `python -m src.etl_historico` "
                   "con los Excel mensuales en la carpeta del histórico.")
        return

    h = data.historico()
    cat = data.historico_cuentas().set_index("CUENTA")["NOMBRE CUENTA"]
    ents = data.historico_entidades()

    # ── Selección ──────────────────────────────────────────────────────────────
    ents = ents.sort_values("ENTIDAD")
    ultimo_corte = h["PERIODO"].astype(str).max()
    etiquetas = {SECTOR: None}
    for _, r in ents.iterrows():
        marca = "" if r["ULTIMO PERIODO"] == ultimo_corte \
            else f"  · hasta {r['ULTIMO PERIODO']}"
        etiquetas[f"{_limpiar(r['ENTIDAD'])} ({r['CODIGO ENTIDAD']}){marca}"] = \
            int(r["CODIGO ENTIDAD"])

    c1, c2 = st.columns([2, 3])
    sel = c1.selectbox("Entidad", etiquetas.keys())
    codigo = etiquetas[sel]

    def _opcion(c):
        return f"{c} · {cat.get(c, '').title()}"

    cuentas = c2.multiselect(
        "Cuentas a graficar", sorted(cat.index), default=CUENTAS_BASE,
        format_func=_opcion,
        help="Todas las cuentas a 6 dígitos del histórico (1.625 códigos).")
    if not cuentas:
        st.info("Selecciona al menos una cuenta.")
        return

    serie = an.serie_historica(h, cuentas, codigo)
    if serie.empty:
        st.info("La entidad no registra saldos en las cuentas seleccionadas.")
        return

    anios = sorted({p[:4] for p in serie.index})
    a1, a2 = st.select_slider("Rango de años", anios, value=(anios[0], anios[-1]))
    serie = serie[(serie.index >= a1) & (serie.index <= f"{a2}-12")]

    # ── KPIs del último corte de la selección ─────────────────────────────────
    ult = serie.index.max()
    st.subheader(f"Último corte de la selección: {ult}")
    kpis = [c for c in ["100000", "140000", "210000", "300000", "350000"]
            if c in serie.columns][:4]
    cols = st.columns(max(len(kpis), 1))
    for i, c in enumerate(kpis):
        var = an.variacion_anual(serie[c].dropna())
        cols[i].metric(cat.get(c, c).title(), pesos(serie[c].iloc[-1]),
                       delta=(f"{var:+.1f}% en 12 meses" if var == var else None))
    st.caption(GLOSARIO)

    # ── Serie temporal ─────────────────────────────────────────────────────────
    largo = (serie.reset_index()
             .melt(id_vars="PERIODO", var_name="CUENTA", value_name="VALOR"))
    largo["Cuenta"] = largo["CUENTA"].map(lambda c: f"{c} · {cat.get(c, '').title()}")
    fig = px.line(largo, x="PERIODO", y="VALOR", color="Cuenta",
                  color_discrete_sequence=PALETA,
                  labels={"PERIODO": "", "VALOR": "Saldo (COP)"})
    fig.update_layout(height=460, margin=dict(l=0, r=0, t=30, b=0),
                      legend=dict(orientation="h", y=-0.15))

    # anotaciones de fusiones/novedades dentro del rango visible
    eventos = EVENTOS.get(codigo, []) if codigo else EVENTOS_SECTOR
    for periodo, texto in eventos:
        if serie.index.min() <= periodo <= ult:
            fig.add_vline(x=periodo, line_dash="dot", line_color="gray")
            fig.add_annotation(x=periodo, y=1, yref="paper", text=texto,
                               showarrow=False, textangle=-90, xshift=-8,
                               font=dict(size=10, color="gray"), yanchor="top")
    st.plotly_chart(fig, width="stretch")
    if eventos:
        st.caption("Las líneas punteadas marcan fusiones y novedades conocidas "
                   "(censo de novedades, jun-2026).")

    # ── Vista de sector: cobertura de reporte ──────────────────────────────────
    if codigo is None:
        with st.expander("Entidades que reportan por mes"):
            n = an.entidades_por_periodo(h)
            fig2 = go.Figure(go.Scatter(x=n.index.astype(str), y=n.values,
                                        mode="lines", line_color=PALETA[1]))
            fig2.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0),
                               yaxis_title="Entidades")
            st.plotly_chart(fig2, width="stretch")
            st.caption("De 181 CAC en 2018 a 169 reportando en abril 2026: "
                       "15 salidas (fusiones, intervenciones y liquidaciones), "
                       "3 entradas por transformación a especializada de ahorro "
                       "y crédito, y algunos atrasos puntuales.")

    # ── Tabla de datos ─────────────────────────────────────────────────────────
    with st.expander("Datos de la serie"):
        tabla = serie.copy()
        tabla.columns = [f"{c} · {cat.get(c, '').title()}" for c in tabla.columns]
        st.dataframe(tabla.style.format(lambda v: pesos(v) if v == v else "—"),
                     width="stretch")
