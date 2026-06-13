"""
analytics.py — Cálculos sobre el DataFrame de entidades (nivel sector/entidad).

A diferencia de indicators.py (lógica pura para un balance suelto), aquí se
trabaja de forma vectorizada sobre todas las entidades a la vez.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src import agrupaciones as ag

# Códigos de cuentas principales usados en los indicadores
A = "100000"   # Activo
P = "200000"   # Pasivo
PAT = "300000"  # Patrimonio
CART = "140000"  # Cartera de créditos
DEP = "210000"  # Depósitos
APO = "310000"  # Capital social (aportes)
EXC = "350000"  # Excedente / pérdida del ejercicio
ING = "400000"  # Ingresos
GTO = "500000"  # Gastos
GADM = "510000"  # Gastos de administración


def _ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    """num/den*100 protegido contra división por cero."""
    return np.where(den != 0, num / den * 100, np.nan)


def agregar_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve una copia de df con columnas de indicadores financieros (%)."""
    d = df.copy()
    d["ROA"] = _ratio(d[EXC], d[A])
    d["SOLVENCIA"] = _ratio(d[PAT], d[A])
    d["ENDEUDAMIENTO"] = _ratio(d[P], d[A])
    d["CARTERA_ACTIVO"] = _ratio(d[CART], d[A])
    d["FONDEO_DEPOSITOS"] = _ratio(d[DEP], d[A])
    d["MARGEN_EXCEDENTE"] = _ratio(d[EXC], d[ING])
    d["EFICIENCIA"] = _ratio(d[GADM], d[ING])
    d["ROE"] = _ratio(d[EXC], d[PAT])
    return d


def indicadores_6dig(saldos: pd.DataFrame) -> pd.DataFrame:
    """
    Indicadores calculados con el catálogo de agrupaciones (cuentas a 6 dígitos),
    portados del proyecto analisis_tasas. Recibe el DataFrame ancho de
    saldos_6dig.parquet (una fila por entidad, una columna por código PUC) y
    devuelve CODIGO ENTIDAD + columnas de indicadores (en %).
    """
    def A(alias: str) -> pd.Series:
        return ag.calcular_df(alias, saldos)

    cb    = A("CARTERA_BRUTA")
    ci    = A("CARTERA_INTEGRAL")
    ri    = A("CARTERA_EN_RIESGO")
    act   = A("ACTIVOS")
    ing   = A("INGRESOS_TOTAL")
    inti  = A("INGRESOS_CARTERA")
    recup = A("RECUPERACIONES")
    gadm  = A("GASTOS_ADMINISTRACION")
    cfin  = A("COSTOS_FINANCIEROS")
    csoc  = A("CAPITAL_SOCIAL")
    ef_den = inti + recup

    out = pd.DataFrame({"CODIGO ENTIDAD": saldos["CODIGO ENTIDAD"].astype(int)})

    # Calidad y cobertura de cartera
    out["CALIDAD_RIESGO"]    = _ratio(ri, ci)
    out["COBERTURA_RIESGO"]  = _ratio(A("PROVISIONES_TOTAL"), ri)
    out["COBERTURA_GENERAL"] = _ratio(
        A("PROVISIONES_INDIVIDUALES_CAPITAL") + A("PROVISIONES_GENERALES"), cb)
    out["CARTERA_PRODUCTIVA"] = _ratio(A("CARTERA_PRODUCTIVA_AB"), cb)

    # Mezcla de cartera por modalidad
    out["PCT_VIVIENDA"]   = _ratio(A("CARTERA_BRUTA_VIVIENDA"), cb)
    out["PCT_CONSUMO"]    = _ratio(A("CARTERA_BRUTA_CONSUMO_LIBRANZA")
                                   + A("CARTERA_BRUTA_CONSUMO_CAJA"), cb)
    out["PCT_MICROCREDITO"] = _ratio(A("CARTERA_BRUTA_MICROCREDITO"), cb)
    out["PCT_COMERCIAL"]  = _ratio(A("CARTERA_BRUTA_COMERCIAL"), cb)
    out["PCT_PRODUCTIVO"] = _ratio(A("CARTERA_BRUTA_PRODUCTIVO")
                                   + A("CARTERA_BRUTA_EMPLEADOS"), cb)

    # Fondeo y estructura
    out["FONDEO_DEP_CARTERA"] = _ratio(A("DEPOSITOS_NETOS"), cb)
    out["FONDEO_APORTES"]     = _ratio(A("APORTES_SOCIALES_ASOCIADOS"), cb)
    out["DEUDA_ACTIVOS"]      = _ratio(A("OBLIGACIONES_FINANCIERAS"), act)
    out["ACTIVOS_IMPRODUCTIVOS"] = _ratio(A("ACTIVO_IMPRODUCTIVO"), act)

    # Capital
    out["CAPITAL_INSTITUCIONAL"] = _ratio(A("CAPITAL_INSTITUCIONAL"), act)
    out["IRREDUCIBLE_SOCIAL"]    = _ratio(A("CAPITAL_IRREDUCIBLE"), csoc)

    # Eficiencia y márgenes (estado de resultados)
    out["EFICIENCIA_OPERATIVA"] = _ratio(gadm + cfin, ef_den)
    out["MARGEN_FINANCIERO"]    = _ratio(inti - cfin, inti)
    out["MARGEN_OPERACIONAL"]   = _ratio(inti + recup - cfin - gadm, inti)
    out["DIVERSIFICACION"]      = _ratio(ing - inti - recup, ing)
    out["DEPENDENCIA_MARGEN"]   = _ratio(ef_den, ing)

    return out


def agregar_indicadores_6dig(df: pd.DataFrame, saldos: pd.DataFrame) -> pd.DataFrame:
    """Cruza el DataFrame de entidades con los indicadores a 6 dígitos."""
    return df.merge(indicadores_6dig(saldos), on="CODIGO ENTIDAD", how="left")


def resumen_sector(df: pd.DataFrame) -> dict:
    """Cifras agregadas del conjunto de entidades recibido."""
    return {
        "entidades": int(len(df)),
        "activo": float(df[A].sum()),
        "pasivo": float(df[P].sum()),
        "patrimonio": float(df[PAT].sum()),
        "cartera": float(df[CART].sum()),
        "depositos": float(df[DEP].sum()),
        "excedente": float(df[EXC].sum()),
        "ingresos": float(df[ING].sum()),
        "asociados": int(df["ASOCIADOS"].sum()),
        "empleados": int(df["EMPLEADOS"].sum()),
    }


def por_grupo(df: pd.DataFrame, col: str, top: int | None = None) -> pd.DataFrame:
    """Agrega activo, entidades y asociados por una columna categórica."""
    g = (df.groupby(col)
         .agg(activo=(A, "sum"), entidades=(A, "size"), asociados=("ASOCIADOS", "sum"))
         .reset_index()
         .sort_values("activo", ascending=False))
    if top:
        g = g.head(top)
    return g.reset_index(drop=True)


def ranking(df: pd.DataFrame, col: str, n: int = 15, ascendente: bool = False) -> pd.DataFrame:
    cols = ["ENTIDAD", "SIGLA", "TIPO ENTIDAD", "DEPARTAMENTO", col]
    cols = [c for c in cols if c in df.columns]
    return (df.sort_values(col, ascending=ascendente)
            .head(n)[cols]
            .reset_index(drop=True))


# ── Histórico mensual CAC ─────────────────────────────────────────────────────

def serie_historica(hist: pd.DataFrame, cuentas: list[str],
                    codigo: int | None = None) -> pd.DataFrame:
    """
    Serie mensual (PERIODO × CUENTA) a partir del histórico largo.
    Si `codigo` es None agrega todo el sector; si no, filtra esa entidad.
    """
    d = hist if codigo is None else hist[hist["CODIGO ENTIDAD"] == codigo]
    d = d[d["CUENTA"].isin(cuentas)]
    piv = d.pivot_table(index="PERIODO", columns="CUENTA", values="VALOR",
                        aggfunc="sum", observed=True)
    piv.columns = piv.columns.astype(str)
    piv.index = piv.index.astype(str)  # PERIODO llega como categórico sin orden
    return piv.sort_index()


def entidades_por_periodo(hist: pd.DataFrame) -> pd.Series:
    """Número de entidades que reportan en cada período."""
    n = hist.groupby("PERIODO", observed=True)["CODIGO ENTIDAD"].nunique()
    n.index = n.index.astype(str)
    return n.sort_index()


def variacion_anual(serie: pd.Series) -> float:
    """Variación % del último dato frente a 12 meses atrás (NaN si no alcanza)."""
    if len(serie) < 13 or serie.iloc[-13] == 0:
        return float("nan")
    return float((serie.iloc[-1] / serie.iloc[-13] - 1) * 100)


CUENTAS_FOTO = [A, P, PAT, CART, DEP, EXC]

# Categorías de CAC por monto de activos (Art. 2.11.13.1.2 del Decreto único).
# Los límites están fijos en UVR; el umbral en pesos = límite × valor de la UVR.
UVR_DIC_2024 = 376.7763  # UVR al 31-dic-2024 (tabla oficial Supersolidaria)
CAT_LIMITES_UVR = (315_000_000, 1_400_000_000)  # Básica|Intermedia, Intermedia|Plena


def categoria_cac(activo, uvr: float = UVR_DIC_2024):
    """Categoría regulatoria por monto de activos: Básica / Intermedia / Plena.
    Acepta un escalar o una Serie. Básica: activos ≤ 315M UVR; Intermedia: hasta
    < 1.400M UVR; Plena: ≥ 1.400M UVR (umbrales en pesos según la UVR dada)."""
    t1, t2 = (lim * uvr for lim in CAT_LIMITES_UVR)
    if isinstance(activo, pd.Series):
        return pd.Series(np.select([activo <= t1, activo < t2],
                                    ["Básica", "Intermedia"], default="Plena"),
                         index=activo.index)
    if activo <= t1:
        return "Básica"
    return "Intermedia" if activo < t2 else "Plena"


# Subcategorías de tamaño (capa analítica, no regulatoria) dentro de cada
# categoría. Fuente única para la UI: categoría → subcategorías de mayor a menor.
SUBCATEGORIAS = {
    "Básica": ["Básica - Grupo 1", "Básica - Grupo 2", "Básica - Grupo 3"],
    "Intermedia": ["Intermedia - Grupo 1", "Intermedia - Grupo 2"],
    "Plena": ["Plena"],
}


def subcategoria_cac(activo, uvr: float = UVR_DIC_2024):
    """Subcategoría de tamaño dentro de la categoría regulatoria. Plena no se
    subdivide. Intermedia: 2 grupos partidos en el punto medio de la banda.
    Básica: 3 grupos = tercios del tope de Básica. Acepta escalar o Serie."""
    t1, t2 = (lim * uvr for lim in CAT_LIMITES_UVR)
    inter_mid = (t1 + t2) / 2          # ~$323 mM
    b1, b2 = t1 / 3, 2 * t1 / 3        # ~$39.6 mM y ~$79.1 mM

    def _una(a):
        if a <= t1:  # Básica
            if a < b1:
                return "Básica - Grupo 3"
            return "Básica - Grupo 2" if a < b2 else "Básica - Grupo 1"
        if a < t2:   # Intermedia
            return "Intermedia - Grupo 2" if a < inter_mid else "Intermedia - Grupo 1"
        return "Plena"

    return activo.map(_una) if isinstance(activo, pd.Series) else _una(activo)


# Período de referencia de la clasificación. La norma usa los activos a 31-dic
# del año anterior (Art. 2.11.13.1.2, Parágrafo 1) y la UVR de esa fecha.
# La clasificación NO se recalcula cada mes: se mantiene fija y se actualiza
# manualmente (aquí) solo cuando la Supersolidaria reclasifique.
#
# Reclasificar exige 3 cierres anuales consecutivos cruzando el umbral, así que
# los cambios son infrecuentes y deliberados. Para actualizar:
#   1) ajustar CATEGORIA_REF_PERIODO al nuevo dic de referencia (y, si cambió la
#      UVR, actualizar UVR_DIC_2024 / el valor usado), o
#   2) usar CATEGORIA_OVERRIDES para forzar la categoría de entidades puntuales.
# Decisión del usuario (2026-06-13): enfoque manual; no automatizar la regla de
# los 3 años (requeriría la UVR de cada 31-dic, que hoy no tenemos).
CATEGORIA_REF_PERIODO = "2024-12"

# Overrides manuales {CODIGO ENTIDAD: "Básica"|"Intermedia"|"Plena"} para
# imponer la categoría oficial cuando difiera del cálculo por activos de
# referencia (p. ej. tras una reclasificación de la Supersolidaria). Vacío hoy.
CATEGORIA_OVERRIDES: dict[int, str] = {}


def activos_referencia(hist: pd.DataFrame,
                       ref_periodo: str = CATEGORIA_REF_PERIODO) -> pd.Series:
    """Activos (cuenta 100000) de cada entidad en el período de referencia.
    Las que no reportan ahí (entraron después) usan su primer período."""
    act = (hist[hist["CUENTA"] == "100000"]
           .pivot_table(index="CODIGO ENTIDAD", columns="PERIODO",
                        values="VALOR", aggfunc="sum", observed=True))
    act.columns = act.columns.astype(str)
    primero = act[sorted(act.columns)].bfill(axis=1).iloc[:, 0]
    ref = act[ref_periodo] if ref_periodo in act.columns else primero
    return ref.fillna(primero)


def clasificar_cac(hist: pd.DataFrame, ref_periodo: str = CATEGORIA_REF_PERIODO,
                   uvr: float = UVR_DIC_2024,
                   overrides: dict[int, str] | None = None) -> pd.DataFrame:
    """Clasificación FIJA por entidad (categoría y subcategoría) según los
    activos del período de referencia. No depende del corte que se visualiza.
    `overrides` impone la categoría oficial de entidades puntuales; su
    subcategoría pasa al Grupo 1 (tope) de la categoría forzada."""
    overrides = CATEGORIA_OVERRIDES if overrides is None else overrides
    ref = activos_referencia(hist, ref_periodo)
    out = pd.DataFrame({
        "CODIGO ENTIDAD": ref.index,
        "ACTIVO_REF": ref.values,
        "CATEGORIA": categoria_cac(ref, uvr).values,
        "SUBCATEGORIA": subcategoria_cac(ref, uvr).values,
    })
    for cod, cat in overrides.items():
        m = out["CODIGO ENTIDAD"] == cod
        out.loc[m, "CATEGORIA"] = cat
        out.loc[m, "SUBCATEGORIA"] = SUBCATEGORIAS[cat][0]  # Grupo 1 por defecto
    return out


def foto_cac(hist: pd.DataFrame, meta: pd.DataFrame,
             periodo: str | None = None) -> tuple[pd.DataFrame, str]:
    """
    Foto del sector CAC en un período del histórico (por defecto el último):
    una fila por entidad con las cuentas principales en columnas, enriquecida
    con los metadatos de `meta` (nombre, sigla, departamento, asociados…).
    Devuelve (DataFrame, período usado).
    """
    per = periodo or str(hist["PERIODO"].astype(str).max())
    d = hist[(hist["PERIODO"].astype(str) == per) & hist["CUENTA"].isin(CUENTAS_FOTO)]
    w = (d.pivot_table(index="CODIGO ENTIDAD", columns="CUENTA", values="VALOR",
                       aggfunc="sum", observed=True)
         .reindex(columns=CUENTAS_FOTO).fillna(0.0))
    w.columns = [str(c) for c in w.columns]
    return w.reset_index().merge(meta, on="CODIGO ENTIDAD", how="left"), per


# ── Agrupaciones (catálogo PUC) sobre el histórico mensual ────────────────────
# El panel PERIODO × CUENTA (saldos del sector sumados) permite aplicar las
# agrupaciones de `agrupaciones.py` a cualquier mes: snapshot y serie temporal.

def panel_mensual(hist: pd.DataFrame, codigos=None) -> pd.DataFrame:
    """Panel ancho PERIODO × CUENTA con los saldos sumados sobre las entidades
    (todas las CAC, o solo las de `codigos`)."""
    d = hist if codigos is None else hist[hist["CODIGO ENTIDAD"].isin(codigos)]
    w = d.pivot_table(index="PERIODO", columns="CUENTA", values="VALOR",
                      aggfunc="sum", observed=True)
    w.columns = w.columns.astype(str)
    w.index = w.index.astype(str)
    # pivot_table deja NaN en (período, cuenta) sin dato; con 0.0 las
    # agrupaciones escalares (`ag.calcular`) no se contaminan de NaN.
    return w.fillna(0.0).sort_index()


def agrupaciones_entidad(hist: pd.DataFrame, periodo: str,
                         aliases: list[str]) -> pd.DataFrame:
    """Monto de cada agrupación del catálogo PUC **por entidad** en un período.

    Pivota el histórico a CODIGO ENTIDAD × CUENTA en el corte dado y aplica
    `ag.calcular_df`. Devuelve CODIGO ENTIDAD + una columna por alias. Permite
    sumar agrupaciones (Cartera bruta, Aportes…) por grupos de entidades."""
    d = hist[hist["PERIODO"].astype(str) == str(periodo)]
    w = d.pivot_table(index="CODIGO ENTIDAD", columns="CUENTA", values="VALOR",
                      aggfunc="sum", observed=True).fillna(0.0)
    w.columns = w.columns.astype(str)
    w = w.reset_index()
    out = pd.DataFrame({"CODIGO ENTIDAD": w["CODIGO ENTIDAD"].astype(int)})
    for alias in aliases:
        out[alias] = ag.calcular_df(alias, w).values
    return out


def serie_alias(panel: pd.DataFrame, alias: str) -> pd.Series:
    """Serie mensual del monto de una agrupación (suma de cuentas del catálogo)."""
    s = ag.calcular_df(alias, panel)
    s.index = panel.index
    return s


def valor_alias(panel: pd.DataFrame, periodo: str, alias: str) -> float:
    """Monto de una agrupación en un período puntual del panel."""
    if periodo not in panel.index:
        return float("nan")
    return float(ag.calcular(alias, panel.loc[periodo].to_dict()))


def ratio_alias(panel: pd.DataFrame, num: str, den: str) -> pd.Series:
    """Serie del cociente num/den (en %) entre dos agrupaciones, protegida."""
    n, d = serie_alias(panel, num), serie_alias(panel, den)
    return (n / d * 100).where(d != 0)


def roa_roe(panel: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """ROA y ROE anualizados (%) por período. El excedente del histórico es
    acumulado del año, así que se anualiza dividiendo por los meses corridos."""
    exc = serie_alias(panel, "EXCEDENTE")
    act = serie_alias(panel, "ACTIVOS")
    pat = serie_alias(panel, "PATRIMONIO")
    meses = pd.Series([int(p[-2:]) for p in panel.index], index=panel.index)
    factor = 12 / meses
    roa = (exc / act * 100 * factor).where(act != 0)
    roe = (exc / pat * 100 * factor).where(pat != 0)
    return roa, roe
