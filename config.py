"""
config.py — Constantes de dominio (fuente de verdad).

Plan Único de Cuentas (PUC) de la Supersolidaria. El primer dígito del código
identifica la clase contable. Los códigos de 6 dígitos son las cuentas con las
que se construyen los indicadores.
"""

# Clases del PUC (primer dígito del código de cuenta)
CLASES_PUC = {
    "1": "Activo",
    "2": "Pasivo",
    "3": "Patrimonio",
    "4": "Ingresos",
    "5": "Gastos",
    "6": "Costos",
}

# Cuentas clave del balance (códigos PUC a 6 dígitos — estándar Supersolidaria)
CUENTAS = {
    "activo":     "100000",
    "pasivo":     "200000",
    "patrimonio": "300000",
    "cartera":    "140000",   # Cartera de créditos
    "depositos":  "210000",   # Depósitos y exigibilidades
    "aportes":    "310500",   # Aportes sociales
    "excedente":  "350000",   # Excedente / pérdida del ejercicio
    "ingresos":   "400000",
    "gastos":     "500000",
    "costos":     "600000",
}

# Nombres legibles para mostrar en la UI
ETIQUETAS = {
    "activo":     "Activo total",
    "pasivo":     "Pasivo total",
    "patrimonio": "Patrimonio",
    "cartera":    "Cartera de créditos",
    "depositos":  "Depósitos",
    "aportes":    "Aportes sociales",
    "excedente":  "Excedente del ejercicio",
}

# ── Catálogo de cuentas principales (código PUC → nombre) ─────────────────────
# Códigos presentes como columnas en el reporte de "cuentas principales".
CATALOGO_CUENTAS = {
    "100000": "ACTIVO",
    "110000": "EFECTIVO Y EQUIVALENTE AL EFECTIVO",
    "120000": "INVERSIONES",
    "130000": "INVENTARIOS",
    "140000": "CARTERA DE CRÉDITOS",
    "160000": "CUENTAS POR COBRAR Y OTRAS",
    "170000": "ACTIVOS MATERIALES",
    "180000": "ACTIVOS NO CORRIENTES MANTENIDOS PARA LA VENTA",
    "190000": "OTROS ACTIVOS",
    "200000": "PASIVOS",
    "210000": "DEPÓSITOS",
    "230000": "OBLIGACIONES FINANCIERAS Y OTROS PASIVOS FINANCIEROS",
    "240000": "CUENTAS POR PAGAR Y OTRAS",
    "250000": "IMPUESTO DIFERIDO PASIVO",
    "260000": "FONDOS SOCIALES Y MUTUALES",
    "270000": "OTROS PASIVOS",
    "280000": "PROVISIONES",
    "300000": "PATRIMONIO",
    "310000": "CAPITAL SOCIAL",
    "310500": "APORTES SOCIALES TEMPORALMENTE RESTRINGIDOS",
    "320000": "RESERVAS",
    "330000": "FONDOS DE DESTINACIÓN ESPECÍFICA",
    "340000": "SUPERÁVIT",
    "350000": "EXCEDENTES Y/O PÉRDIDAS DEL EJERCICIO",
    "360000": "RESULTADOS ACUMULADOS POR ADOPCIÓN POR PRIMERA VEZ",
    "400000": "INGRESOS",
    "410000": "INGRESOS POR VENTA DE BIENES Y SERVICIOS",
    "420000": "OTROS INGRESOS",
    "500000": "GASTOS",
    "510000": "GASTOS DE ADMINISTRACIÓN",
    "520000": "OTROS GASTOS",
    "530000": "EXCEDENTES Y PÉRDIDAS DEL EJERCICIO",
    "540000": "GASTOS DE VENTAS",
    "600000": "COSTO DE VENTAS",
    "610000": "COSTO DE VENTAS Y DE PRESTACIÓN DE SERVICIOS",
    "620000": "COMPRAS",
    "810000": "DEUDORAS CONTINGENTES",
    "830000": "DEUDORAS DE CONTROL",
    "840000": "DEUDORA - CLASIFICACIÓN DE LA CARTERA POR MOROSIDAD",
    "860000": "DEUDORAS CONTINGENTES POR CONTRA (CR)",
    "880000": "DEUDORAS DE CONTROL POR CONTRA (CR)",
    "910000": "ACREEDORAS CONTINGENTES",
    "930000": "ACREEDORAS DE CONTROL",
    "960000": "ACREEDORAS POR CONTRA (DB)",
    "980000": "ACREEDORAS DE CONTROL POR CONTRA (CR)",
}

# Columnas de datos básicos en el reporte de cuentas principales
COLS_BASICAS = [
    "CODIGO ENTIDAD", "ENTIDAD", "NIT", "SIGLA", "TIPO ENTIDAD", "CIIU",
    "ACTIVIDAD ECONOMICA", "REPRESENTANTE LEGAL", "DEPARTAMENTO", "MUNICIPIO",
    "DIRECCION", "TELEFONO", "EMAIL", "NIVEL DE SUPERVISION", "ASOCIADOS",
    "EMPLEADOS", "CATEGORIA",
]

# Rutas de datos
import os as _os
_BASE = _os.path.dirname(_os.path.abspath(__file__))
DATA_RAW = _os.path.join(_BASE, "data", "raw")
DATA_PROC = _os.path.join(_BASE, "data", "processed")

# Archivos fuente (corte marzo 2026; ahorro y crédito a abril 2026)
ARCHIVOS = {
    "principales": "20260519_estados_financieros_cuentas_principales_marzo_2026.xlsx",
    "seisdig":     "20260519_estados_financieros_6dig_marzo_2026.xlsx",
    "cac_abril":   "20260601_estados_financieros_ahorro_credito_abril.xlsx",
    "desviacion":  "20260428_desviacion_estandar_marzo_2026.xlsx",
    "var":         "20260413_var_mar_26.xlsx",
    "tasas":       "20260515_tasas__deleg_finan_marzo.xlsx",
}
