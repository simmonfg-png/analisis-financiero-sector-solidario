"""
agrupaciones.py — Catálogo único de agrupaciones de cuentas PUC.

Portado del proyecto `analisis_tasas` (financiero/agrupaciones.py), donde estas
fórmulas están verificadas contra los balances reales de cooperativas vigiladas
por la Supersolidaria. Es la fuente de verdad de los conceptos financieros que
se calculan a partir del plan de cuentas a 6 dígitos.

Cada agrupación define un concepto financiero como suma ponderada de cuentas:
    cuentas: [(codigo_puc, signo), ...]   signo: +1 suma, -1 resta
o como composición de otras agrupaciones:
    componentes: ["ALIAS", {"alias": "ALIAS", "signo": -1}, ...]

Estructura de cada entrada:
    alias       clave única (MAYÚSCULAS_GUIÓN_BAJO)
    nombre      etiqueta legible para la UI
    categoria   agrupación de primer nivel
    descripcion propósito del concepto (opcional)
"""
from __future__ import annotations

import pandas as pd

# ══════════════════════════════════════════════════════════════════════════════
# BALANCE — ESTRUCTURA GENERAL
# ══════════════════════════════════════════════════════════════════════════════

BALANCE_ESTRUCTURA = [
    {
        "alias":       "ACTIVOS",
        "nombre":      "Activos Totales",
        "categoria":   "Balance",
        "descripcion": "Total activos (clase 1 del PUC)",
        "cuentas":     [("100000", +1)],
    },
    {
        "alias":       "PASIVOS",
        "nombre":      "Pasivos Totales",
        "categoria":   "Balance",
        "descripcion": "Total pasivos (clase 2 del PUC)",
        "cuentas":     [("200000", +1)],
    },
    {
        "alias":       "PATRIMONIO",
        "nombre":      "Patrimonio",
        "categoria":   "Balance",
        "descripcion": "Total patrimonio (clase 3 del PUC)",
        "cuentas":     [("300000", +1)],
    },
    {
        "alias":       "EXCEDENTE",
        "nombre":      "Excedente del Ejercicio",
        "categoria":   "Balance",
        "descripcion": "Excedente acumulado del período (cuenta 350000)",
        "cuentas":     [("350000", +1)],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# BALANCE — CARTERA DE CRÉDITO
# ══════════════════════════════════════════════════════════════════════════════

BALANCE_CARTERA = [
    {
        "alias":       "CARTERA_BRUTA_VIVIENDA",
        "nombre":      "Cartera Bruta Vivienda",
        "categoria":   "Cartera",
        "descripcion": "Capital cartera modalidad Vivienda",
        "cuentas":     [("140400", +1), ("140500", +1)],
    },
    {
        "alias":       "CARTERA_BRUTA_CONSUMO_LIBRANZA",
        "nombre":      "Cartera Bruta Consumo Libranza",
        "categoria":   "Cartera",
        "descripcion": "Capital cartera modalidad Consumo Libranza",
        "cuentas":     [("141100", +1), ("144100", +1)],
    },
    {
        "alias":       "CARTERA_BRUTA_CONSUMO_CAJA",
        "nombre":      "Cartera Bruta Consumo Caja",
        "categoria":   "Cartera",
        "descripcion": "Capital cartera modalidad Consumo Caja",
        "cuentas":     [("141200", +1), ("144200", +1)],
    },
    {
        "alias":       "CARTERA_BRUTA_MICROCREDITO",
        "nombre":      "Cartera Bruta Microcrédito",
        "categoria":   "Cartera",
        "descripcion": "Capital cartera modalidad Microcrédito (incluye histórica 144800)",
        "cuentas":     [("144800", +1), ("145400", +1), ("145500", +1)],
    },
    {
        "alias":       "CARTERA_BRUTA_COMERCIAL",
        "nombre":      "Cartera Bruta Comercial",
        "categoria":   "Cartera",
        "descripcion": "Capital cartera modalidad Comercial",
        "cuentas":     [("146100", +1), ("146200", +1)],
    },
    {
        "alias":       "CARTERA_BRUTA_EMPLEADOS",
        "nombre":      "Cartera Bruta Empleados",
        "categoria":   "Cartera",
        "descripcion": "Capital cartera modalidad Empleados (cuenta histórica 146900)",
        "cuentas":     [("146900", +1)],
    },
    {
        "alias":       "CARTERA_BRUTA_PRODUCTIVO",
        "nombre":      "Cartera Bruta Productivo",
        "categoria":   "Cartera",
        "descripcion": "Capital cartera modalidad Productivo",
        "cuentas":     [("147600", +1)],
    },
    {
        "alias":       "CARTERA_BRUTA",
        "nombre":      "Cartera Bruta",
        "categoria":   "Cartera",
        "descripcion": "Capital total de cartera por todas las modalidades (solo capital, sin intereses ni otros conceptos)",
        "componentes": [
            "CARTERA_BRUTA_VIVIENDA",
            "CARTERA_BRUTA_CONSUMO_LIBRANZA",
            "CARTERA_BRUTA_CONSUMO_CAJA",
            "CARTERA_BRUTA_MICROCREDITO",
            "CARTERA_BRUTA_COMERCIAL",
            "CARTERA_BRUTA_EMPLEADOS",
            "CARTERA_BRUTA_PRODUCTIVO",
        ],
    },
    {
        "alias":       "CARTERA_PRODUCTIVA_AB",
        "nombre":      "Cartera Productiva (A + B)",
        "categoria":   "Cartera",
        "descripcion": "Subcuentas de categorías A y B por modalidad. Incluye modalidades históricas inactivas para compatibilidad.",
        "cuentas": [
            ("140405", +1), ("140410", +1), ("140505", +1), ("140510", +1),
            ("144105", +1), ("144110", +1), ("144205", +1), ("144210", +1),
            ("144805", +1), ("144810", +1),
            ("145405", +1), ("145410", +1),
            ("145505", +1), ("145510", +1),
            ("146205", +1), ("146210", +1),
            ("146905", +1), ("146910", +1), ("146930", +1), ("146935", +1),
            ("147605", +1), ("147610", +1),
        ],
    },
    {
        "alias":       "PROVISIONES_INDIVIDUALES_CAPITAL",
        "nombre":      "Provisiones Individuales — Capital",
        "categoria":   "Cartera",
        "descripcion": "Provisiones individuales sobre el capital de cartera por modalidad",
        "cuentas": [
            ("140800", +1), ("144500", +1), ("145800", +1),
            ("146500", +1), ("147100", +1), ("147900", +1),
        ],
    },
    {
        "alias":       "PROVISIONES_INDIVIDUALES_INTERES",
        "nombre":      "Provisiones Individuales — Interés",
        "categoria":   "Cartera",
        "descripcion": "Provisiones individuales sobre intereses causados por modalidad",
        "cuentas": [
            ("140900", +1), ("144600", +1), ("145900", +1),
            ("146600", +1), ("147200", +1), ("148000", +1),
        ],
    },
    {
        "alias":       "PROVISIONES_INDIVIDUALES_OTROS",
        "nombre":      "Provisiones Individuales — Otros Conceptos",
        "categoria":   "Cartera",
        "descripcion": "Provisiones individuales sobre otros conceptos de cartera por modalidad",
        "cuentas": [
            ("141000", +1), ("144700", +1), ("146000", +1),
            ("146700", +1), ("147500", +1), ("148100", +1),
        ],
    },
    {
        "alias":       "PROVISIONES_INDIVIDUALES",
        "nombre":      "Provisiones Individuales",
        "categoria":   "Cartera",
        "descripcion": "Total provisiones individuales (capital + interés + otros conceptos)",
        "componentes": [
            "PROVISIONES_INDIVIDUALES_CAPITAL",
            "PROVISIONES_INDIVIDUALES_INTERES",
            "PROVISIONES_INDIVIDUALES_OTROS",
        ],
    },
    {
        "alias":       "PROVISIONES_GENERALES",
        "nombre":      "Provisiones Generales",
        "categoria":   "Cartera",
        "descripcion": "Provisión general (cuenta 146800)",
        "cuentas":     [("146800", +1)],
    },
    {
        "alias":       "PROVISIONES_TOTAL",
        "nombre":      "Provisiones Totales",
        "categoria":   "Cartera",
        "descripcion": "Suma de provisiones individuales y generales",
        "componentes": ["PROVISIONES_INDIVIDUALES", "PROVISIONES_GENERALES"],
    },
    {
        "alias":       "CASTIGOS",
        "nombre":      "Castigos de Cartera",
        "categoria":   "Cartera",
        "descripcion": "Cartera castigada acumulada (cuenta contingente 831015)",
        "cuentas":     [("831015", +1)],
    },
    {
        "alias":       "CARTERA_INTEGRAL",
        "nombre":      "Cartera con Interés y Otros Conceptos",
        "categoria":   "Cartera",
        "descripcion": "Cartera incluyendo capital, intereses causados y otros conceptos por modalidad. Denominador de Cobertura General.",
        "cuentas": [
            ("140400", +1), ("140500", +1), ("140600", +1), ("140700", +1),
            ("141100", +1), ("141200", +1),
            ("144100", +1), ("144200", +1), ("144300", +1), ("144400", +1),
            ("145400", +1), ("145500", +1), ("145600", +1), ("145700", +1),
            ("146100", +1), ("146200", +1), ("146300", +1), ("146400", +1),
            ("146900", +1),
            ("147000", +1), ("147400", +1), ("147600", +1), ("147700", +1),
            ("147800", +1),
        ],
    },
    # ── Cartera en Riesgo — Capital por modalidad ────────────────────────────
    {
        "alias":       "CARTERA_RIESGO_VIVIENDA_CAPITAL",
        "nombre":      "Cartera en Riesgo Vivienda — Capital",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) modalidad Vivienda",
        "cuentas": [
            ("140410", +1), ("140415", +1), ("140420", +1), ("140425", +1),
            ("140510", +1), ("140515", +1), ("140520", +1), ("140525", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_CONSUMO_LIBRANZA_CAPITAL",
        "nombre":      "Cartera en Riesgo Consumo Libranza — Capital",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) modalidad Consumo Libranza",
        "cuentas": [
            ("141110", +1), ("141115", +1), ("141120", +1), ("141125", +1),
            ("144110", +1), ("144115", +1), ("144120", +1), ("144125", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_CONSUMO_CAJA_CAPITAL",
        "nombre":      "Cartera en Riesgo Consumo Caja — Capital",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) modalidad Consumo Caja",
        "cuentas": [
            ("141210", +1), ("141215", +1), ("141220", +1), ("141225", +1),
            ("144210", +1), ("144215", +1), ("144220", +1), ("144225", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_MICROCREDITO_CAPITAL",
        "nombre":      "Cartera en Riesgo Microcrédito — Capital",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) modalidad Microcrédito",
        "cuentas": [
            ("145510", +1), ("145515", +1), ("145520", +1), ("145525", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_COMERCIAL_CAPITAL",
        "nombre":      "Cartera en Riesgo Comercial — Capital",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) modalidad Comercial",
        "cuentas": [
            ("146110", +1), ("146115", +1), ("146120", +1), ("146125", +1),
            ("146210", +1), ("146215", +1), ("146220", +1), ("146225", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_PRODUCTIVO_CAPITAL",
        "nombre":      "Cartera en Riesgo Productivo — Capital",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) modalidad Productivo",
        "cuentas": [
            ("147610", +1), ("147615", +1), ("147620", +1), ("147625", +1),
        ],
    },
    # ── Cartera en Riesgo — Intereses por modalidad ──────────────────────────
    {
        "alias":       "CARTERA_RIESGO_VIVIENDA_INTERESES",
        "nombre":      "Cartera en Riesgo Vivienda — Intereses",
        "categoria":   "Cartera",
        "descripcion": "Intereses causados en riesgo (B-E) modalidad Vivienda",
        "cuentas": [
            ("140610", +1), ("140615", +1), ("140620", +1), ("140625", +1), ("140630", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_CONSUMO_INTERESES",
        "nombre":      "Cartera en Riesgo Consumo — Intereses",
        "categoria":   "Cartera",
        "descripcion": "Intereses causados en riesgo (B-E) modalidades Consumo (Libranza + Caja)",
        "cuentas": [
            ("144310", +1), ("144315", +1), ("144320", +1), ("144325", +1), ("144330", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_MICROCREDITO_INTERESES",
        "nombre":      "Cartera en Riesgo Microcrédito — Intereses",
        "categoria":   "Cartera",
        "descripcion": "Intereses causados en riesgo (B-E) modalidad Microcrédito",
        "cuentas": [
            ("145610", +1), ("145615", +1), ("145620", +1), ("145625", +1), ("145630", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_COMERCIAL_INTERESES",
        "nombre":      "Cartera en Riesgo Comercial — Intereses",
        "categoria":   "Cartera",
        "descripcion": "Intereses causados en riesgo (B-E) modalidad Comercial",
        "cuentas": [
            ("146310", +1), ("146315", +1), ("146320", +1), ("146325", +1), ("146330", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_PRODUCTIVO_INTERESES",
        "nombre":      "Cartera en Riesgo Productivo — Intereses",
        "categoria":   "Cartera",
        "descripcion": "Intereses causados en riesgo (B-E) modalidad Productivo",
        "cuentas": [
            ("147710", +1), ("147715", +1), ("147720", +1), ("147725", +1), ("147730", +1),
        ],
    },
    # ── Cartera en Riesgo — Otros conceptos por modalidad ───────────────────
    {
        "alias":       "CARTERA_RIESGO_VIVIENDA_OTROS",
        "nombre":      "Cartera en Riesgo Vivienda — Otros",
        "categoria":   "Cartera",
        "descripcion": "Otros conceptos en riesgo (B-E) modalidad Vivienda",
        "cuentas": [
            ("140710", +1), ("140715", +1), ("140720", +1), ("140725", +1), ("140730", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_CONSUMO_OTROS",
        "nombre":      "Cartera en Riesgo Consumo — Otros",
        "categoria":   "Cartera",
        "descripcion": "Otros conceptos en riesgo (B-E) modalidades Consumo (Libranza + Caja)",
        "cuentas": [
            ("144410", +1), ("144415", +1), ("144420", +1), ("144425", +1), ("144430", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_MICROCREDITO_OTROS",
        "nombre":      "Cartera en Riesgo Microcrédito — Otros",
        "categoria":   "Cartera",
        "descripcion": "Otros conceptos en riesgo (B-E) modalidad Microcrédito",
        "cuentas": [
            ("145710", +1), ("145715", +1), ("145720", +1), ("145725", +1), ("145730", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_COMERCIAL_OTROS",
        "nombre":      "Cartera en Riesgo Comercial — Otros",
        "categoria":   "Cartera",
        "descripcion": "Otros conceptos en riesgo (B-E) modalidad Comercial",
        "cuentas": [
            ("146410", +1), ("146415", +1), ("146420", +1), ("146425", +1), ("146430", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_PRODUCTIVO_OTROS",
        "nombre":      "Cartera en Riesgo Productivo — Otros",
        "categoria":   "Cartera",
        "descripcion": "Otros conceptos en riesgo (B-E) modalidad Productivo",
        "cuentas": [
            ("147810", +1), ("147815", +1), ("147820", +1), ("147825", +1), ("147830", +1),
        ],
    },
    # ── Cartera en Riesgo — Empleados (B-E) ─────────────────────────────────
    {
        "alias":       "CARTERA_RIESGO_EMPLEADOS_CAPITAL",
        "nombre":      "Cartera en Riesgo Empleados — Capital",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) modalidad Empleados (dos sub-grupos)",
        "cuentas": [
            ("146910", +1), ("146915", +1), ("146920", +1), ("146925", +1),
            ("146935", +1), ("146940", +1), ("146945", +1), ("146950", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_EMPLEADOS_INTERESES",
        "nombre":      "Cartera en Riesgo Empleados — Intereses",
        "categoria":   "Cartera",
        "descripcion": "Intereses causados en riesgo (B-E) modalidad Empleados",
        "cuentas": [
            ("147010", +1), ("147015", +1), ("147020", +1), ("147025", +1),
            ("147035", +1), ("147040", +1), ("147045", +1), ("147050", +1),
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_EMPLEADOS_OTROS",
        "nombre":      "Cartera en Riesgo Empleados — Otros",
        "categoria":   "Cartera",
        "descripcion": "Otros conceptos en riesgo (B-E) modalidad Empleados",
        "cuentas": [
            ("147410", +1), ("147415", +1), ("147420", +1), ("147425", +1),
        ],
    },
    # ── Cartera en Riesgo — Compuestas ───────────────────────────────────────
    {
        "alias":       "CARTERA_RIESGO_CAPITAL",
        "nombre":      "Cartera en Riesgo — Capital Total",
        "categoria":   "Cartera",
        "descripcion": "Capital en riesgo (B-E) todas las modalidades",
        "componentes": [
            "CARTERA_RIESGO_VIVIENDA_CAPITAL",
            "CARTERA_RIESGO_CONSUMO_LIBRANZA_CAPITAL",
            "CARTERA_RIESGO_CONSUMO_CAJA_CAPITAL",
            "CARTERA_RIESGO_MICROCREDITO_CAPITAL",
            "CARTERA_RIESGO_COMERCIAL_CAPITAL",
            "CARTERA_RIESGO_EMPLEADOS_CAPITAL",
            "CARTERA_RIESGO_PRODUCTIVO_CAPITAL",
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_INTERESES",
        "nombre":      "Cartera en Riesgo — Intereses Total",
        "categoria":   "Cartera",
        "descripcion": "Intereses causados en riesgo (B-E) todas las modalidades",
        "componentes": [
            "CARTERA_RIESGO_VIVIENDA_INTERESES",
            "CARTERA_RIESGO_CONSUMO_INTERESES",
            "CARTERA_RIESGO_MICROCREDITO_INTERESES",
            "CARTERA_RIESGO_COMERCIAL_INTERESES",
            "CARTERA_RIESGO_EMPLEADOS_INTERESES",
            "CARTERA_RIESGO_PRODUCTIVO_INTERESES",
        ],
    },
    {
        "alias":       "CARTERA_RIESGO_OTROS",
        "nombre":      "Cartera en Riesgo — Otros Total",
        "categoria":   "Cartera",
        "descripcion": "Otros conceptos en riesgo (B-E) todas las modalidades",
        "componentes": [
            "CARTERA_RIESGO_VIVIENDA_OTROS",
            "CARTERA_RIESGO_CONSUMO_OTROS",
            "CARTERA_RIESGO_MICROCREDITO_OTROS",
            "CARTERA_RIESGO_COMERCIAL_OTROS",
            "CARTERA_RIESGO_EMPLEADOS_OTROS",
            "CARTERA_RIESGO_PRODUCTIVO_OTROS",
        ],
    },
    {
        "alias":       "CARTERA_EN_RIESGO",
        "nombre":      "Cartera en Riesgo (B-E)",
        "categoria":   "Cartera",
        "descripcion": "Total cartera en riesgo (capital + intereses + otros) categorías B-E",
        "componentes": [
            "CARTERA_RIESGO_CAPITAL",
            "CARTERA_RIESGO_INTERESES",
            "CARTERA_RIESGO_OTROS",
        ],
    },
    {
        "alias":       "CONVENIOS",
        "nombre":      "Convenios por Cobrar",
        "categoria":   "Cartera",
        "descripcion": "Intereses y convenios causados por cobrar de cartera (cuenta 147300). Componente de Activos Improductivos.",
        "cuentas":     [("147300", +1)],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# BALANCE — CAPTACIONES / DEPÓSITOS
# ══════════════════════════════════════════════════════════════════════════════

BALANCE_DEPOSITOS = [
    {
        "alias":       "AHORRO_VISTA",
        "nombre":      "Ahorro a la Vista",
        "categoria":   "Depósitos",
        "descripcion": "Saldo bruto de ahorro a la vista (cuenta 210500)",
        "cuentas":     [("210500", +1)],
    },
    {
        "alias":       "CDAT_NETO",
        "nombre":      "CDAT Sin Intereses",
        "categoria":   "Depósitos",
        "descripcion": "CDAT descontando intereses causados (211000 - 211095)",
        "cuentas":     [("211000", +1), ("211095", -1)],
    },
    {
        "alias":       "AHORRO_CONTRACTUAL_NETO",
        "nombre":      "Ahorro Contractual Sin Intereses",
        "categoria":   "Depósitos",
        "descripcion": "Ahorro contractual/programado neto (212500 - 212595)",
        "cuentas":     [("212500", +1), ("212595", -1)],
    },
    {
        "alias":       "DEPOSITOS_NETOS",
        "nombre":      "Depósitos Totales Sin Intereses",
        "categoria":   "Depósitos",
        "descripcion": "Suma de todos los depósitos descontando intereses causados",
        "componentes": ["AHORRO_VISTA", "CDAT_NETO", "AHORRO_CONTRACTUAL_NETO"],
    },
    {
        "alias":       "DEPOSITOS_BRUTOS",
        "nombre":      "Depósitos con Intereses",
        "categoria":   "Depósitos",
        "descripcion": "Total depósitos incluyendo intereses causados (cuenta 210000)",
        "cuentas":     [("210000", +1)],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# BALANCE — CAPITAL Y PATRIMONIO
# ══════════════════════════════════════════════════════════════════════════════

BALANCE_CAPITAL = [
    {
        "alias":       "CAPITAL_SOCIAL",
        "nombre":      "Capital Social",
        "categoria":   "Capital",
        "descripcion": "Capital social total (cuenta 310000)",
        "cuentas":     [("310000", +1)],
    },
    {
        "alias":       "CAPITAL_IRREDUCIBLE",
        "nombre":      "Capital Mínimo Irreducible",
        "categoria":   "Capital",
        "descripcion": "Porción irreducible del capital social (cuenta 311000)",
        "cuentas":     [("311000", +1)],
    },
    {
        "alias":       "APORTES_AMORTIZADOS",
        "nombre":      "Aportes Amortizados",
        "categoria":   "Capital",
        "descripcion": "Aportes en proceso de amortización/devolución (cuenta 311010)",
        "cuentas":     [("311010", +1)],
    },
    {
        "alias":       "CAPITAL_INSTITUCIONAL",
        "nombre":      "Capital Institucional",
        "categoria":   "Capital",
        "descripcion": "Reservas, fondos sociales y donaciones (311010+320000+330000+340000)",
        "cuentas": [
            ("311010", +1), ("320000", +1),
            ("330000", +1), ("340000", +1),
        ],
    },
    {
        "alias":       "APORTES_SOCIALES_ASOCIADOS",
        "nombre":      "Aportes Sociales Asociados",
        "categoria":   "Capital",
        "descripcion": "Capital social descontando aportes en amortización. Usado en Fondeo por Aportes.",
        "cuentas":     [("310000", +1), ("311010", -1)],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# BALANCE — ACTIVOS LÍQUIDOS E IMPRODUCTIVOS
# ══════════════════════════════════════════════════════════════════════════════

BALANCE_LIQUIDEZ = [
    {
        "alias":       "INVERSIONES_VISTA",
        "nombre":      "Inversiones a la Vista",
        "categoria":   "Liquidez",
        "descripcion": "Inversiones en FIC y títulos de alta liquidez (120000 - 122600)",
        "cuentas":     [("120000", +1), ("122600", -1)],
    },
    {
        "alias":       "INVERSIONES_PATRIMONIALES",
        "nombre":      "Inversiones Patrimoniales",
        "categoria":   "Liquidez",
        "descripcion": "Inversiones patrimoniales en otras entidades (122600)",
        "cuentas":     [("122600", +1)],
    },
    {
        "alias":       "EQUIVALENTES_EFECTIVO",
        "nombre":      "Equivalentes de Efectivo",
        "categoria":   "Liquidez",
        "descripcion": "Depósitos e instrumentos con liquidez inmediata (cuenta 111500)",
        "cuentas":     [("111500", +1)],
    },
    {
        "alias":       "EFECTIVO_RESTRINGIDO",
        "nombre":      "Efectivo Restringido",
        "categoria":   "Liquidez",
        "descripcion": "Efectivo restringido o de uso limitado — fondo de liquidez (cuenta 112000)",
        "cuentas":     [("112000", +1)],
    },
    {
        "alias":       "ACTIVO_PRODUCTIVO",
        "nombre":      "Activo Productivo",
        "categoria":   "Liquidez",
        "descripcion": "Activos que generan rendimiento: cartera productiva A+B + equivalentes de efectivo + efectivo restringido + inversiones a la vista.",
        "componentes": [
            "CARTERA_PRODUCTIVA_AB",
            "EQUIVALENTES_EFECTIVO",
            "EFECTIVO_RESTRINGIDO",
            "INVERSIONES_VISTA",
        ],
    },
    {
        "alias":       "CARTERA_NETA",
        "nombre":      "Cartera Neta",
        "categoria":   "Liquidez",
        "descripcion": "Valor neto de cartera reportado en balance (cuenta 140000)",
        "cuentas":     [("140000", +1)],
    },
    # ── Activos Improductivos ─────────────────────────────────────────────────
    {
        "alias":       "CARTERA_IMPRODUCTIVA_CAPITAL",
        "nombre":      "Cartera Improductiva — Capital",
        "categoria":   "Liquidez",
        "descripcion": "Capital de cartera en categorías C, D, E (Bruta menos Productiva A+B)",
        "componentes": [
            {"alias": "CARTERA_BRUTA",         "signo": +1},
            {"alias": "CARTERA_PRODUCTIVA_AB", "signo": -1},
        ],
    },
    {
        "alias":       "INTERESES_CARTERA",
        "nombre":      "Intereses de Cartera",
        "categoria":   "Liquidez",
        "descripcion": "Intereses causados de cartera por modalidad (todas las categorías)",
        "cuentas": [
            ("140600", +1), ("144300", +1), ("144900", +1),
            ("145600", +1), ("146300", +1), ("147000", +1), ("147700", +1),
        ],
    },
    {
        "alias":       "OTROS_CONCEPTOS_CARTERA",
        "nombre":      "Otros Conceptos de Cartera",
        "categoria":   "Liquidez",
        "descripcion": "Otros conceptos de cartera por modalidad (cuentas 7xx de cada grupo)",
        "cuentas": [
            ("140700", +1), ("144400", +1), ("145000", +1),
            ("145700", +1), ("146400", +1), ("147400", +1), ("147800", +1),
        ],
    },
    {
        "alias":       "CARTERA_IMPRODUCTIVA_TOTAL",
        "nombre":      "Cartera Improductiva Total",
        "categoria":   "Liquidez",
        "descripcion": "Capital improductivo + intereses + otros conceptos de cartera",
        "componentes": [
            "CARTERA_IMPRODUCTIVA_CAPITAL",
            "INTERESES_CARTERA",
            "OTROS_CONCEPTOS_CARTERA",
        ],
    },
    {
        "alias":       "CAPITAL_TRABAJO_IMPRODUCTIVO",
        "nombre":      "Capital de Trabajo Improductivo",
        "categoria":   "Liquidez",
        "descripcion": "Caja y bancos sin rendimiento (110500 + 111000)",
        "cuentas":     [("110500", +1), ("111000", +1)],
    },
    {
        "alias":       "OTRAS_CUENTAS_POR_COBRAR",
        "nombre":      "Otras Cuentas por Cobrar",
        "categoria":   "Liquidez",
        "descripcion": "Convenios por cobrar y otras cuentas por cobrar (147300 + 160000)",
        "cuentas":     [("147300", +1), ("160000", +1)],
    },
    {
        "alias":       "ACTIVOS_FIJOS",
        "nombre":      "Activos Fijos",
        "categoria":   "Liquidez",
        "descripcion": "Propiedades, planta y equipo (cuenta 170000)",
        "cuentas":     [("170000", +1)],
    },
    {
        "alias":       "ACTIVOS_PARA_VENTA",
        "nombre":      "Activos para la Venta",
        "categoria":   "Liquidez",
        "descripcion": "Bienes realizables y activos para la venta (cuenta 180000)",
        "cuentas":     [("180000", +1)],
    },
    {
        "alias":       "OTROS_ACTIVOS",
        "nombre":      "Otros Activos",
        "categoria":   "Liquidez",
        "descripcion": "Otros activos no clasificados (cuenta 190000)",
        "cuentas":     [("190000", +1)],
    },
    {
        "alias":       "OTROS_ACTIVOS_IMPRODUCTIVOS",
        "nombre":      "Otros Activos Improductivos",
        "categoria":   "Liquidez",
        "descripcion": "Cuentas por cobrar, activos fijos, para venta y otros",
        "componentes": [
            "OTRAS_CUENTAS_POR_COBRAR",
            "ACTIVOS_FIJOS",
            "ACTIVOS_PARA_VENTA",
            "OTROS_ACTIVOS",
        ],
    },
    {
        "alias":       "ACTIVO_IMPRODUCTIVO",
        "nombre":      "Activo Improductivo",
        "categoria":   "Liquidez",
        "descripcion": "Total de activos que no generan rendimiento, neto de provisiones",
        "componentes": [
            "CARTERA_IMPRODUCTIVA_TOTAL",
            "CAPITAL_TRABAJO_IMPRODUCTIVO",
            "OTROS_ACTIVOS_IMPRODUCTIVOS",
            "INVERSIONES_PATRIMONIALES",
            {"alias": "PROVISIONES_TOTAL", "signo": -1},
        ],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# PASIVOS — OBLIGACIONES FINANCIERAS
# ══════════════════════════════════════════════════════════════════════════════

PASIVOS = [
    {
        "alias":       "INTERESES_OBLIGACIONES_FINANCIERAS",
        "nombre":      "Intereses Obligaciones Financieras",
        "categoria":   "Pasivos",
        "descripcion": "Intereses causados sobre obligaciones financieras por tipo",
        "cuentas": [
            ("230535", +1), ("230830", +1), ("231595", +1), ("231795", +1),
            ("232595", +1), ("234595", +1), ("235095", +1),
        ],
    },
    {
        "alias":       "OBLIGACIONES_FINANCIERAS_CAPITAL",
        "nombre":      "Obligaciones Financieras Sin Intereses",
        "categoria":   "Pasivos",
        "descripcion": "Saldo capital de obligaciones financieras",
        "cuentas": [
            ("230000", +1),
            ("230535", -1), ("230830", -1), ("231595", -1), ("231795", -1),
            ("232595", -1), ("234595", -1), ("235095", -1),
        ],
    },
    {
        "alias":       "OBLIGACIONES_FINANCIERAS",
        "nombre":      "Total Obligaciones Financieras",
        "categoria":   "Pasivos",
        "descripcion": "Total con intereses causados. Usado en Deuda/Activos y Activo Productivo/Pasivo con Costo.",
        "componentes": ["OBLIGACIONES_FINANCIERAS_CAPITAL", "INTERESES_OBLIGACIONES_FINANCIERAS"],
    },
    {
        "alias":       "PASIVO_CON_COSTO",
        "nombre":      "Pasivo con Costo",
        "categoria":   "Pasivos",
        "descripcion": "Pasivos que generan costo financiero: depósitos sin intereses + obligaciones financieras sin intereses.",
        "componentes": ["DEPOSITOS_NETOS", "OBLIGACIONES_FINANCIERAS_CAPITAL"],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# ESTADO DE RESULTADOS
# ══════════════════════════════════════════════════════════════════════════════

ESTADO_RESULTADOS = [
    {
        "alias":       "INGRESOS_TOTAL",
        "nombre":      "Ingresos Totales",
        "categoria":   "Estado de Resultados",
        "descripcion": "Total ingresos (cuenta 400000)",
        "cuentas":     [("400000", +1)],
    },
    {
        "alias":       "INGRESOS_CARTERA",
        "nombre":      "Ingresos de Cartera",
        "categoria":   "Estado de Resultados",
        "descripcion": "Intereses y rendimientos de cartera de crédito (cuenta 415000)",
        "cuentas":     [("415000", +1)],
    },
    {
        "alias":       "RECUPERACIONES",
        "nombre":      "Recuperaciones",
        "categoria":   "Estado de Resultados",
        "descripcion": "Recuperaciones de cartera castigada y deterioro (cuenta 422500)",
        "cuentas":     [("422500", +1)],
    },
    {
        "alias":       "OTROS_INGRESOS",
        "nombre":      "Otros Ingresos Operacionales",
        "categoria":   "Estado de Resultados",
        "descripcion": "Ingresos diferentes a cartera y recuperaciones (420000 - 422500)",
        "cuentas":     [("420000", +1), ("422500", -1)],
    },
    {
        "alias":       "GASTOS_ADMINISTRACION",
        "nombre":      "Gastos Operacionales",
        "categoria":   "Estado de Resultados",
        "descripcion": "Total gastos administrativos y operacionales (cuenta 510000)",
        "cuentas":     [("510000", +1)],
    },
    {
        "alias":       "BENEFICIOS_EMPLEADOS",
        "nombre":      "Beneficios a Empleados",
        "categoria":   "Estado de Resultados",
        "descripcion": "Sueldos, prestaciones y seguridad social (cuenta 510500)",
        "cuentas":     [("510500", +1)],
    },
    {
        "alias":       "GASTOS_GENERALES",
        "nombre":      "Gastos Generales",
        "categoria":   "Estado de Resultados",
        "descripcion": "Arrendamientos, servicios, papelería y otros generales (cuenta 511000)",
        "cuentas":     [("511000", +1)],
    },
    {
        "alias":       "DETERIORO_PROVISIONES",
        "nombre":      "Deterioro y Provisiones",
        "categoria":   "Estado de Resultados",
        "descripcion": "Gasto por deterioro de cartera y provisiones (cuenta 511500)",
        "cuentas":     [("511500", +1)],
    },
    {
        "alias":       "GASTOS_DIVERSOS",
        "nombre":      "Gastos Diversos",
        "categoria":   "Estado de Resultados",
        "descripcion": "Multas, sanciones, gastos extraordinarios y otros (cuenta 520000)",
        "cuentas":     [("520000", +1)],
    },
    {
        "alias":       "COSTOS_FINANCIEROS",
        "nombre":      "Costo Total",
        "categoria":   "Estado de Resultados",
        "descripcion": "Total intereses pagados sobre captaciones y obligaciones (cuenta 600000)",
        "cuentas":     [("600000", +1)],
    },
    {
        "alias":       "COSTOS_DEPOSITOS",
        "nombre":      "Costos Intereses Depósitos",
        "categoria":   "Estado de Resultados",
        "descripcion": "Intereses pagados sobre ahorro a la vista, CDAT y contractual",
        "cuentas": [
            ("615005", +1), ("615010", +1), ("615015", +1),
        ],
    },
    {
        "alias":       "COSTOS_OBLIG_FINANCIERAS",
        "nombre":      "Costos Obligaciones Financieras",
        "categoria":   "Estado de Resultados",
        "descripcion": "Intereses sobre créditos obtenidos de entidades financieras (cuenta 615035)",
        "cuentas":     [("615035", +1)],
    },
    {
        "alias":       "GASTOS_TOTAL",
        "nombre":      "Gastos Totales",
        "categoria":   "Estado de Resultados",
        "descripcion": "Total gastos operacionales (cuenta 500000)",
        "cuentas":     [("500000", +1)],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# ÍNDICE GLOBAL — todas las categorías en orden
# ══════════════════════════════════════════════════════════════════════════════

TODAS = (
    BALANCE_ESTRUCTURA
    + BALANCE_CARTERA
    + BALANCE_DEPOSITOS
    + BALANCE_CAPITAL
    + BALANCE_LIQUIDEZ
    + PASIVOS
    + ESTADO_RESULTADOS
)

# Acceso rápido por alias
POR_ALIAS: dict = {agr["alias"]: agr for agr in TODAS}


def flatten_cuentas(alias: str) -> set[str]:
    """
    Conjunto plano de códigos PUC que entran en la agrupación.
    Resuelve compuestos recursivamente; devuelve solo los códigos (sin signos).
    """
    agr = POR_ALIAS[alias]
    if "cuentas" in agr:
        return {c for c, _ in agr["cuentas"]}
    ctas: set[str] = set()
    for comp in agr["componentes"]:
        nombre = comp if isinstance(comp, str) else comp["alias"]
        ctas |= flatten_cuentas(nombre)
    return ctas


def cuentas_necesarias() -> set[str]:
    """Todos los códigos PUC usados por el catálogo (para filtrar en el ETL)."""
    ctas: set[str] = set()
    for alias in POR_ALIAS:
        ctas |= flatten_cuentas(alias)
    return ctas


def calcular(alias: str, saldos: dict) -> float:
    """
    Valor de una agrupación dado un dict {cuenta: saldo}.
    Cuentas ausentes aportan 0.
    """
    agr = POR_ALIAS[alias]
    if "cuentas" in agr:
        return sum(saldos.get(cta, 0.0) * signo for cta, signo in agr["cuentas"])
    total = 0.0
    for comp in agr["componentes"]:
        if isinstance(comp, str):
            total += calcular(comp, saldos)
        else:
            total += calcular(comp["alias"], saldos) * comp["signo"]
    return total


def calcular_df(alias: str, df: pd.DataFrame) -> pd.Series:
    """
    Versión vectorizada de `calcular`: opera sobre un DataFrame con una fila
    por entidad y una columna por código PUC. Columnas ausentes aportan 0.
    """
    agr = POR_ALIAS[alias]
    total = pd.Series(0.0, index=df.index)
    if "cuentas" in agr:
        for cta, signo in agr["cuentas"]:
            if cta in df.columns:
                total = total + pd.to_numeric(df[cta], errors="coerce").fillna(0.0) * signo
        return total
    for comp in agr["componentes"]:
        if isinstance(comp, str):
            total = total + calcular_df(comp, df)
        else:
            total = total + calcular_df(comp["alias"], df) * comp["signo"]
    return total
