"""
loader.py — Lectura de los Excel/CSV de balance publicados por la
Superintendencia de Economía Solidaria.

El formato típico trae, entre otras, columnas de:
  - código de cuenta (PUC)   p.ej. CODRENGLON / CUENTA / CODIGO
  - descripción              p.ej. DESCRIPCION / NOMBRE
  - saldo                    p.ej. SALDO / VALOR

Esta función detecta esas columnas de forma flexible y devuelve un DataFrame
normalizado con: cuenta (str) | descripcion (str) | saldo (float).
"""
from __future__ import annotations

import pandas as pd

# Posibles nombres de columna (en mayúsculas, sin acentos) → campo normalizado
_ALIASES = {
    "cuenta":      ["codrenglon", "cuenta", "codigo", "codcuenta", "cod_cuenta", "renglon"],
    "descripcion": ["descripcion", "nombre", "concepto", "detalle"],
    "saldo":       ["saldo", "valor", "monto", "saldofinal"],
}


def _normalizar(col: str) -> str:
    s = str(col).strip().lower()
    for a, b in zip("áéíóúñ", "aeioun"):
        s = s.replace(a, b)
    return s.replace(" ", "").replace("_", "")


def _detectar(columnas) -> dict:
    """Mapea {campo_normalizado: nombre_real_en_el_archivo}."""
    norm = {_normalizar(c): c for c in columnas}
    encontrado = {}
    for campo, alias in _ALIASES.items():
        for a in alias:
            if a in norm:
                encontrado[campo] = norm[a]
                break
    return encontrado


def cargar_balance(ruta_o_buffer) -> pd.DataFrame:
    """
    Lee un balance (Excel .xlsx/.xls o CSV) y lo normaliza.

    Devuelve un DataFrame con columnas: cuenta | descripcion | saldo.
    Lanza ValueError si no puede identificar las columnas mínimas.
    """
    nombre = getattr(ruta_o_buffer, "name", str(ruta_o_buffer)).lower()
    if nombre.endswith(".csv"):
        df = pd.read_csv(ruta_o_buffer, sep=None, engine="python",
                         dtype=str, encoding="latin-1")
    else:
        df = pd.read_excel(ruta_o_buffer, dtype=str)

    cols = _detectar(df.columns)
    faltan = [c for c in ("cuenta", "saldo") if c not in cols]
    if faltan:
        raise ValueError(
            f"No se encontraron las columnas requeridas {faltan}. "
            f"Columnas del archivo: {list(df.columns)}"
        )

    out = pd.DataFrame()
    out["cuenta"]      = df[cols["cuenta"]].astype(str).str.strip()
    out["descripcion"] = (df[cols["descripcion"]].astype(str).str.strip()
                          if "descripcion" in cols else "")
    out["saldo"]       = _a_numero(df[cols["saldo"]])

    # Quitar filas sin código de cuenta válido
    out = out[out["cuenta"].str.replace(".", "", regex=False).str.isdigit()]
    return out.reset_index(drop=True)


def _a_numero(serie: pd.Series) -> pd.Series:
    """Convierte texto con separadores de miles/decimales a float."""
    s = (serie.astype(str)
         .str.replace(r"[^\d,.\-]", "", regex=True)
         .str.replace(".", "", regex=False)   # separador de miles
         .str.replace(",", ".", regex=False)) # separador decimal
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def saldo_de(df: pd.DataFrame, cuenta: str) -> float:
    """Saldo de una cuenta PUC concreta (0.0 si no existe)."""
    fila = df.loc[df["cuenta"] == cuenta, "saldo"]
    return float(fila.iloc[0]) if not fila.empty else 0.0
