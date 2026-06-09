"""
format.py — Formateo de cifras para la UI (pesos colombianos, porcentajes).
"""
from __future__ import annotations


def pesos(v: float, decimales: int = 1) -> str:
    """Formato compacto en pesos: B (billón), mM (mil millones), M (millón)."""
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e12:
        return f"${v / 1e12:,.{decimales}f} B"
    if a >= 1e9:
        return f"${v / 1e9:,.{decimales}f} mM"
    if a >= 1e6:
        return f"${v / 1e6:,.{decimales}f} M"
    return f"${v:,.0f}"


def pesos_full(v: float) -> str:
    """Pesos con separador de miles, sin abreviar."""
    return f"${v:,.0f}" if v is not None else "—"


def pct(v: float, decimales: int = 1) -> str:
    if v is None or (isinstance(v, float) and v != v):  # NaN
        return "—"
    return f"{v:.{decimales}f}%"


def miles(v) -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "—"


def cantidad(v) -> str:
    """Conteo compacto para KPIs: 7.0 M, 12.3 k, 950."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(v) >= 1e6:
        return f"{v / 1e6:,.1f} M"
    if abs(v) >= 10_000:
        return f"{v / 1e3:,.1f} k"
    return f"{int(v):,}"


# Glosario de sufijos para mostrar al usuario
GLOSARIO = "Cifras en pesos: **B** = billones (10¹²) · **mM** = miles de millones · **M** = millones."
