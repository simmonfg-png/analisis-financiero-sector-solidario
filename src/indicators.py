"""
indicators.py — Cálculo de indicadores financieros a partir del balance.

Lógica PURA (sin Streamlit ni pandas): recibe un dict {cuenta: saldo} o valores
sueltos y devuelve números. Así es fácil de probar con pytest y reutilizar en
reportes o procesos batch.
"""
from __future__ import annotations

from config import CUENTAS


def _val(balance: dict, clave: str) -> float:
    """Saldo de una cuenta lógica (p.ej. 'activo') a partir del dict {cuenta: saldo}."""
    return float(balance.get(CUENTAS[clave], 0.0))


# ── Indicadores individuales (puros) ─────────────────────────────────────────

def indice_solvencia(patrimonio: float, activo: float) -> float:
    """Patrimonio como % del activo total. Mayor = más solvente."""
    return (patrimonio / activo * 100) if activo else 0.0


def cartera_sobre_activo(cartera: float, activo: float) -> float:
    """Qué porcentaje del activo está colocado en cartera de créditos."""
    return (cartera / activo * 100) if activo else 0.0


def fondeo_por_depositos(depositos: float, activo: float) -> float:
    """Depósitos como % del activo (cuánto se fondea con ahorro de asociados)."""
    return (depositos / activo * 100) if activo else 0.0


def margen_excedente(excedente: float, ingresos: float) -> float:
    """Excedente como % de los ingresos."""
    return (excedente / ingresos * 100) if ingresos else 0.0


def roa(excedente: float, activo: float) -> float:
    """Retorno sobre activos (proxy con saldos puntuales)."""
    return (excedente / activo * 100) if activo else 0.0


# ── Cálculo agregado desde un balance ────────────────────────────────────────

def calcular_indicadores(balance: dict) -> dict:
    """
    Recibe {cuenta_puc: saldo} y devuelve un dict de indicadores listos para la UI.
    """
    activo     = _val(balance, "activo")
    pasivo     = _val(balance, "pasivo")
    patrimonio = _val(balance, "patrimonio")
    cartera    = _val(balance, "cartera")
    depositos  = _val(balance, "depositos")
    excedente  = _val(balance, "excedente")
    ingresos   = _val(balance, "ingresos")

    return {
        "Activo":                 activo,
        "Pasivo":                 pasivo,
        "Patrimonio":             patrimonio,
        "Índice de solvencia (%)":  round(indice_solvencia(patrimonio, activo), 2),
        "Cartera / Activo (%)":     round(cartera_sobre_activo(cartera, activo), 2),
        "Fondeo por depósitos (%)": round(fondeo_por_depositos(depositos, activo), 2),
        "Margen de excedente (%)":  round(margen_excedente(excedente, ingresos), 2),
        "ROA (%)":                  round(roa(excedente, activo), 2),
    }
