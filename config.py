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
