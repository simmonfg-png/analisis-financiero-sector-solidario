"""
etl.py — Pipeline de consolidación de los reportes de la Supersolidaria.

Lee los Excel originales (data/raw/) y produce tablas limpias en parquet
(data/processed/) que la app consume de forma instantánea:

    entidades.parquet        Maestro de 1.467 entidades + cuentas principales (marzo)
    tasas.parquet            Tasas activas/pasivas ponderadas por entidad (marzo)
    cac_abril.parquet        Cuentas a 6 dígitos de las CAC (abril)
    riesgo_cartera.parquet   Serie histórica del indicador de cartera y umbrales σ
    var_factores.parquet     Medias y desviaciones de factores de riesgo de mercado
    var_correlacion.parquet  Matriz de correlación entre factores

Uso:  python -m src.etl     (o)     python src/etl.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (  # noqa: E402
    ARCHIVOS, CATALOGO_CUENTAS, COLS_BASICAS, DATA_PROC, DATA_RAW,
)


def _raw(clave: str) -> str:
    return os.path.join(DATA_RAW, ARCHIVOS[clave])


def _proc(nombre: str) -> str:
    return os.path.join(DATA_PROC, nombre)


def _norm(s) -> str:
    """Normaliza un encabezado: sin acentos, sin espacios extra, en mayúsculas."""
    s = str(s).strip().upper()
    for a, b in zip("ÁÉÍÓÚÑ", "AEIOUN"):
        s = s.replace(a, b)
    while "  " in s:
        s = s.replace("  ", " ")
    return s


# ── 1. Maestro de entidades + cuentas principales ────────────────────────────
def construir_entidades() -> pd.DataFrame:
    df = pd.read_excel(_raw("principales"), header=8)
    df.columns = [str(c).strip() for c in df.columns]

    # Renombrar columnas básicas a una forma canónica (tolerante a espacios)
    canon = {_norm(c): c for c in COLS_BASICAS}
    ren = {}
    for c in df.columns:
        if _norm(c) in canon:
            ren[c] = canon[_norm(c)]
    df = df.rename(columns=ren)

    # Quedarnos solo con filas de entidad (código numérico)
    df = df[pd.to_numeric(df["CODIGO ENTIDAD"], errors="coerce").notna()].copy()
    df["CODIGO ENTIDAD"] = df["CODIGO ENTIDAD"].astype(int)

    # Columnas de cuenta: enteros tipo 100000 → string "100000"
    cuenta_cols = {}
    for c in df.columns:
        cc = str(c).replace(".0", "").strip()
        if cc.isdigit() and cc in CATALOGO_CUENTAS:
            cuenta_cols[c] = cc
    df = df.rename(columns=cuenta_cols)

    # Tipos numéricos
    for cc in CATALOGO_CUENTAS:
        if cc in df.columns:
            df[cc] = pd.to_numeric(df[cc], errors="coerce").fillna(0.0)
    for c in ("ASOCIADOS", "EMPLEADOS"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # Limpieza de texto
    for c in df.select_dtypes("object").columns:
        df[c] = df[c].astype(str).str.strip().replace({"nan": "", "None": ""})

    base = [c for c in COLS_BASICAS if c in df.columns]
    cuentas = [c for c in CATALOGO_CUENTAS if c in df.columns]
    return df[base + cuentas].reset_index(drop=True)


# ── 2. Tasas activas y pasivas ───────────────────────────────────────────────
def construir_tasas() -> pd.DataFrame:
    raw = pd.read_excel(_raw("tasas"), sheet_name="Marzo", header=3)
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw[pd.to_numeric(raw["Cod Entidad"], errors="coerce").notna()].copy()

    out = pd.DataFrame()
    out["CODIGO ENTIDAD"] = raw["Cod Entidad"].astype(int)
    out["SIGLA"] = raw["Entidad"].astype(str).str.strip()
    out["SEGMENTO"] = raw["Segmento"].astype(str).str.strip()
    out["DEPARTAMENTO"] = raw["Depto"].astype(str).str.strip()

    # Activa: Consumo, Vivienda, Comercial, Microcredito, Total Activa
    # Pasiva: CDAT, Permanente, Contractual, Cuenta de ahorro, Total Pasiva
    mapa = {
        "Consumo": "ACT_CONSUMO", "Vivienda": "ACT_VIVIENDA",
        "Comercial": "ACT_COMERCIAL", "Microcredito": "ACT_MICROCREDITO",
        "Total Activa": "TASA_ACTIVA",
        "CDAT": "PAS_CDAT", "Permanente": "PAS_PERMANENTE",
        "Contractual": "PAS_CONTRACTUAL", "Cuenta de ahorro": "PAS_AHORRO",
        "Total Pasiva": "TASA_PASIVA",
    }
    for orig, dest in mapa.items():
        col = next((c for c in raw.columns if _norm(c) == _norm(orig)), None)
        out[dest] = pd.to_numeric(raw[col], errors="coerce") if col else pd.NA

    # Margen de intermediación
    out["MARGEN"] = out["TASA_ACTIVA"] - out["TASA_PASIVA"]
    return out.reset_index(drop=True)


# ── 3. Detalle 6 dígitos de las CAC (abril) ──────────────────────────────────
def construir_cac_abril() -> pd.DataFrame:
    """El archivo viene transpuesto: filas=cuentas, columnas=entidades."""
    raw = pd.read_excel(_raw("cac_abril"), header=None)
    # Fila 6: códigos de entidad (desde col 2); fila 8: NIT; datos desde fila 9
    cod_row = raw.iloc[6].tolist()
    nom_row = raw.iloc[7].tolist()
    ent_cols = {}
    for j in range(2, raw.shape[1]):
        cod = pd.to_numeric(cod_row[j], errors="coerce")
        if pd.notna(cod):
            ent_cols[j] = (int(cod), str(nom_row[j]).strip())

    registros = []
    for i in range(9, raw.shape[0]):
        cuenta = pd.to_numeric(raw.iat[i, 0], errors="coerce")
        if pd.isna(cuenta):
            continue
        cuenta = str(int(cuenta))
        nombre = str(raw.iat[i, 1]).strip()
        for j, (cod, _sig) in ent_cols.items():
            val = pd.to_numeric(raw.iat[i, j], errors="coerce")
            if pd.notna(val) and val != 0:
                registros.append((cod, cuenta, nombre, float(val)))

    out = pd.DataFrame(registros, columns=["CODIGO ENTIDAD", "CUENTA", "NOMBRE CUENTA", "VALOR"])
    return out


# ── 4. Serie histórica del indicador de cartera (desviación estándar) ─────────
def construir_riesgo_cartera() -> pd.DataFrame:
    raw = pd.read_excel(_raw("desviacion"), header=6)
    raw.columns = [str(c).strip() for c in raw.columns]
    raw = raw.dropna(how="all")
    # Primera columna numérica (#) marca filas de datos
    primera = raw.columns[0]
    raw = raw[pd.to_numeric(raw[primera], errors="coerce").notna()].copy()

    out = pd.DataFrame()
    out["PERIODO"] = raw.iloc[:, 1].astype(str).str.strip()
    out["INDICADOR_CARTERA"] = pd.to_numeric(raw.iloc[:, 2], errors="coerce")
    out["DESV_ESTANDAR"] = pd.to_numeric(raw.iloc[:, 3], errors="coerce")
    if raw.shape[1] > 4:
        out["PROM_MAS_1_SIGMA"] = pd.to_numeric(raw.iloc[:, 4], errors="coerce")
    if raw.shape[1] > 5:
        out["PROM_MAS_2_SIGMA"] = pd.to_numeric(raw.iloc[:, 5], errors="coerce")
    return out.dropna(subset=["INDICADOR_CARTERA"]).reset_index(drop=True)


# ── 5. VaR: factores y correlaciones ─────────────────────────────────────────
def construir_var():
    f = _raw("var")
    fac = pd.read_excel(f, sheet_name="03-26 Matriz y desviaciones", header=9)
    fac.columns = [str(c).strip() for c in fac.columns]
    fac = fac.dropna(how="all", axis=1).dropna(how="all")
    # Columnas esperadas: #, FACTOR, MEDIA, DESVIACIÓN
    cols = [c for c in fac.columns if _norm(c) in ("FACTOR", "MEDIA", "DESVIACION")]
    factor_col = next((c for c in fac.columns if _norm(c) == "FACTOR"), None)
    fac = fac[fac[factor_col].notna()] if factor_col else fac
    factores = fac[[factor_col] + [c for c in cols if c != factor_col]].copy() if factor_col else fac

    corr = pd.read_excel(f, sheet_name="03-26 Matriz de correlacion", header=9)
    corr = corr.dropna(how="all", axis=1).dropna(how="all")
    corr = corr.rename(columns={corr.columns[0]: "FACTOR"})
    corr = corr[corr["FACTOR"].notna()].reset_index(drop=True)
    # Conservar solo filas de factores reales (descartar notas al pie) y
    # forzar a numéricas las columnas de coeficientes.
    nombres = set(corr["FACTOR"].astype(str)) & set(corr.columns)
    corr = corr[corr["FACTOR"].isin(nombres)].reset_index(drop=True)
    for c in corr.columns:
        if c != "FACTOR":
            corr[c] = pd.to_numeric(corr[c], errors="coerce")
    corr = corr.dropna(how="all", axis=1)
    return factores.reset_index(drop=True), corr


# ── Orquestador ──────────────────────────────────────────────────────────────
def main():
    os.makedirs(DATA_PROC, exist_ok=True)
    pasos = [
        ("entidades.parquet", construir_entidades),
        ("tasas.parquet", construir_tasas),
        ("cac_abril.parquet", construir_cac_abril),
        ("riesgo_cartera.parquet", construir_riesgo_cartera),
    ]
    for nombre, fn in pasos:
        df = fn()
        df.to_parquet(_proc(nombre), index=False)
        print(f"✓ {nombre:28s} {len(df):>8,} filas  ×  {df.shape[1]} cols")

    factores, corr = construir_var()
    factores.to_parquet(_proc("var_factores.parquet"), index=False)
    corr.to_parquet(_proc("var_correlacion.parquet"), index=False)
    print(f"✓ {'var_factores.parquet':28s} {len(factores):>8,} filas")
    print(f"✓ {'var_correlacion.parquet':28s} {len(corr):>8,} filas")
    print("\nETL completado.")


if __name__ == "__main__":
    main()
