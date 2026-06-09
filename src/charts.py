"""
charts.py — Helpers de visualización con Plotly.
"""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go


def torta_estructura(activo: float, pasivo: float, patrimonio: float) -> go.Figure:
    """Composición Pasivo vs. Patrimonio sobre el Activo."""
    fig = px.pie(
        names=["Pasivo", "Patrimonio"],
        values=[max(pasivo, 0), max(patrimonio, 0)],
        title="Estructura financiera (Pasivo vs. Patrimonio)",
        hole=0.45,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def barras_indicadores(indicadores: dict) -> go.Figure:
    """Barras con los indicadores expresados en porcentaje."""
    pct = {k: v for k, v in indicadores.items() if k.endswith("(%)")}
    fig = px.bar(
        x=list(pct.keys()),
        y=list(pct.values()),
        title="Indicadores clave (%)",
        labels={"x": "", "y": "%"},
        text=list(pct.values()),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    return fig
