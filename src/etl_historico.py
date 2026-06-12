"""ETL del histórico mensual de estados financieros de las CAC (2018-01 → hoy).

Lee los Excel de la carpeta "ESTADOS FINANCIEROS COOPERATIVAS DE AHORRO Y
CREDITO" (formato transpuesto de la Supersolidaria: cuentas en filas,
entidades en columnas) y produce:

- data/processed/historico_cac.parquet   — formato largo:
    PERIODO (YYYY-MM) · CODIGO ENTIDAD · CUENTA · VALOR
- data/processed/historico_cuentas.parquet — catálogo CUENTA → NOMBRE CUENTA
    (el nombre más reciente observado).
- data/processed/historico_entidades.parquet — CODIGO ENTIDAD → NIT y nombre
    más recientes + primer/último período reportado.

El layout cambia entre épocas (filas de título variables, columna
"NOMBRE ENTIDAD" presente solo en los archivos viejos, .xls vs .xlsx),
por eso las filas de encabezado se localizan dinámicamente.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_HIST = RAIZ / "ESTADOS FINANCIEROS COOPERATIVAS DE AHORRO Y CREDITO"
PROCESSED = RAIZ / "data" / "processed"

PATRON_NOMBRE = re.compile(r"(\d{4}) - (\d{2}) - ")


def _reparar_texto(s: pd.Series) -> pd.Series:
    """Repara la codificación dañada de los Excel fuente: aparece un \\x90
    espurio pegado a las 'É' (o en lugar de ellas) y la 'Ñ' de algunos
    nombres de entidad llega como '??'."""
    return (s.str.replace("É\x90", "É", regex=False)
            .str.replace("\x90É", "É", regex=False)
            .str.replace("\x90", "É", regex=False)
            .str.replace("ANTIOQUE??A", "ANTIOQUEÑA", regex=False)
            .str.replace("CR??DITO", "CRÉDITO", regex=False))


def _localizar(df: pd.DataFrame, etiqueta: str, max_filas: int = 15,
               max_cols: int = 6) -> tuple[int, int] | None:
    """Devuelve (fila, columna) de la celda cuyo texto es `etiqueta`."""
    for i in range(min(max_filas, len(df))):
        for j in range(min(max_cols, df.shape[1])):
            if str(df.iat[i, j]).strip().upper() == etiqueta:
                return i, j
    return None


def leer_mes(ruta: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Lee un Excel mensual → (saldos largos, entidades, cuentas) del período."""
    m = PATRON_NOMBRE.match(ruta.name)
    if not m:
        raise ValueError(f"Nombre de archivo sin período: {ruta.name}")
    periodo = f"{m.group(1)}-{m.group(2)}"

    motor = "xlrd" if ruta.suffix.lower() == ".xls" else "openpyxl"
    xl = pd.ExcelFile(ruta, engine=motor)
    df = xl.parse(xl.sheet_names[0], header=None)  # la primera hoja es la de datos

    pos_cod = _localizar(df, "CODIGO ENTIDAD")
    pos_cta = _localizar(df, "CUENTA")
    if pos_cod is None or pos_cta is None:
        raise ValueError(f"{ruta.name}: no se hallaron los encabezados")
    fila_cod, _ = pos_cod
    fila_cta, col_cta = pos_cta
    # fila de NIT: en los archivos viejos tiene etiqueta "NIT"; en los nuevos
    # (2026) es la fila siguiente al encabezado, sin rótulo — se reconoce por
    # el patrón ###-###-###-#
    pos_nit = _localizar(df, "NIT", max_filas=fila_cta + 3)
    if pos_nit is None and fila_cta + 1 < len(df):
        candidata = df.iloc[fila_cta + 1].astype(str).str.strip()
        if candidata.str.fullmatch(r"[\d-]{7,}").sum() > len(candidata) / 3:
            pos_nit = (fila_cta + 1, 0)

    # columnas de entidades = las que tienen código numérico en la fila de códigos
    codigos = pd.to_numeric(df.iloc[fila_cod], errors="coerce")
    cols_ent = codigos[codigos.notna()].index.tolist()
    codigos = codigos[cols_ent].astype(int)

    nits = (df.iloc[pos_nit[0], cols_ent].astype(str).str.strip()
            if pos_nit else pd.Series("", index=cols_ent))
    # nombre de la entidad: fila donde está la etiqueta CUENTA (archivos viejos
    # la rotulan "NOMBRE ENTIDAD"; en los nuevos es la misma fila de nombres)
    nombres = _reparar_texto(df.iloc[fila_cta, cols_ent].astype(str).str.strip())

    cuerpo = df.iloc[fila_cta + 1:]
    cuentas = cuerpo[col_cta].astype(str).str.strip()
    es_cuenta = cuentas.str.fullmatch(r"\d+")
    cuerpo = cuerpo[es_cuenta]
    cuentas = cuentas[es_cuenta]
    # cuentas repetidas dentro de un mismo archivo: quedarse con la última
    # aparición (caso real: mayo 2021 trae 100000 dos veces y solo la última
    # cuadra con pasivo + patrimonio del mes)
    ultimas = ~cuentas.duplicated(keep="last")
    cuerpo = cuerpo[ultimas]
    cuentas = cuentas[ultimas]
    nombres_cta = _reparar_texto(cuerpo[col_cta + 1].astype(str).str.strip())

    valores = cuerpo[cols_ent].apply(pd.to_numeric, errors="coerce")
    valores.columns = codigos.values
    valores.index = cuentas.values

    # enero 2020: los valores vienen corridos una fila hacia abajo respecto a
    # las etiquetas (la fila del total 100000 queda vacía y la de 110000 trae
    # el activo total). Se detecta por la fila 100000 vacía y se realinea,
    # validando que activo = pasivo + patrimonio tras el ajuste.
    if "100000" in valores.index and valores.loc["100000"].isna().all():
        ajustado = valores.shift(-1)
        a, p, pt = (ajustado.loc[c].sum() for c in ("100000", "200000", "300000"))
        if abs(a - p - pt) < 1e6:
            valores = ajustado
        else:
            raise ValueError(f"{ruta.name}: fila 100000 vacía y el realineo no cuadra")

    largo = valores.stack().rename("VALOR").reset_index()
    largo.columns = ["CUENTA", "CODIGO ENTIDAD", "VALOR"]
    largo = largo[largo["VALOR"] != 0]  # sin saldo == no informativo
    largo.insert(0, "PERIODO", periodo)

    ent_mes = pd.DataFrame({
        "CODIGO ENTIDAD": codigos.values,
        "NIT": nits.values,
        "ENTIDAD": nombres.values,
        "PERIODO": periodo,
    })
    ctas_mes = pd.DataFrame({
        "CUENTA": cuentas.values, "NOMBRE CUENTA": nombres_cta.values,
        "PERIODO": periodo,
    })
    return largo, ent_mes, ctas_mes


def construir_historico() -> None:
    archivos = sorted(p for p in CARPETA_HIST.iterdir()
                      if PATRON_NOMBRE.match(p.name))
    partes, ents, ctas = [], [], []
    for ruta in archivos:
        parte, ent_mes, ctas_mes = leer_mes(ruta)
        partes.append(parte)
        ents.append(ent_mes)
        ctas.append(ctas_mes)
        print(f"  {parte['PERIODO'].iat[0]}: {parte['CODIGO ENTIDAD'].nunique()} "
              f"entidades, {parte['CUENTA'].nunique()} cuentas, {len(parte):,} saldos")

    hist = pd.concat(partes, ignore_index=True)

    # validación: activo = pasivo + patrimonio en todos los períodos
    piv = (hist[hist["CUENTA"].isin(["100000", "200000", "300000"])]
           .pivot_table(index="PERIODO", columns="CUENTA", values="VALOR",
                        aggfunc="sum"))
    desc = (piv["100000"] - piv["200000"] - piv["300000"]).abs()
    malos = desc[piv.isna().any(axis=1) | (desc > 1e6)]
    if len(malos):
        raise ValueError(f"Períodos descuadrados o sin totales: {list(malos.index)}")

    hist["CUENTA"] = hist["CUENTA"].astype("category")
    hist["PERIODO"] = hist["PERIODO"].astype("category")
    hist.to_parquet(PROCESSED / "historico_cac.parquet", index=False)

    # catálogo de cuentas: nombre más reciente observado por código
    cat = (pd.concat(ctas, ignore_index=True)
           .sort_values("PERIODO")
           .drop_duplicates("CUENTA", keep="last")
           .drop(columns="PERIODO")
           .sort_values("CUENTA"))
    cat.to_parquet(PROCESSED / "historico_cuentas.parquet", index=False)

    # catálogo de entidades: datos más recientes + rango reportado;
    # el NIT se toma del último período donde venga informado
    e = pd.concat(ents, ignore_index=True).sort_values("PERIODO")
    e["NIT"] = e["NIT"].replace({"nan": "", "None": ""})
    rango = e.groupby("CODIGO ENTIDAD")["PERIODO"].agg(["min", "max"])
    rango.columns = ["PRIMER PERIODO", "ULTIMO PERIODO"]
    nit = (e[e["NIT"] != ""].drop_duplicates("CODIGO ENTIDAD", keep="last")
           .set_index("CODIGO ENTIDAD")["NIT"])
    ent_cat = (e.drop_duplicates("CODIGO ENTIDAD", keep="last")
               .drop(columns=["PERIODO", "NIT"])
               .merge(rango, on="CODIGO ENTIDAD")
               .sort_values("CODIGO ENTIDAD"))
    ent_cat.insert(1, "NIT", ent_cat["CODIGO ENTIDAD"].map(nit).fillna(""))
    ent_cat.to_parquet(PROCESSED / "historico_entidades.parquet", index=False)

    print(f"\nhistorico_cac.parquet: {len(hist):,} filas, "
          f"{hist['PERIODO'].nunique()} períodos, "
          f"{hist['CODIGO ENTIDAD'].nunique()} entidades, "
          f"{hist['CUENTA'].nunique()} cuentas")
    for nombre in ("historico_cac", "historico_cuentas", "historico_entidades"):
        ruta = PROCESSED / f"{nombre}.parquet"
        print(f"  {nombre}.parquet: {ruta.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    construir_historico()
