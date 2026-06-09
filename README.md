# Análisis Financiero del Sector Solidario

Interfaz web (Streamlit) para analizar la situación financiera de las entidades
del sector solidario a partir de los balances publicados por la
**Superintendencia de Economía Solidaria**. Carga el Excel/CSV, calcula
indicadores a partir de las cuentas PUC y los visualiza para apoyar la toma de
decisiones.

## Estructura

```
ANALISIS FINANCIERO SECTOR SOLIDARIO/
├── app.py              # Punto de entrada Streamlit (UI)
├── config.py           # Constantes de dominio (cuentas PUC)
├── requirements.txt
├── data/               # Balances .xlsx/.csv (ignorados en git)
├── src/
│   ├── loader.py       # Lee y normaliza el Excel/CSV de la Supersolidaria
│   ├── indicators.py   # Cálculo de indicadores (lógica pura, testeable)
│   └── charts.py       # Gráficas Plotly
└── tests/
    └── test_indicators.py
```

## Puesta en marcha (Windows / PowerShell)

```powershell
# 1. Entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Dependencias
pip install -r requirements.txt

# 3. Arrancar la app
streamlit run app.py
```

La app abre en el navegador (http://localhost:8501). Sube un balance desde la
propia interfaz para ver las métricas y gráficas.

## Tests

```powershell
pytest
```

## Próximos pasos sugeridos

- Soportar **varios períodos** (comparativo y evolución histórica).
- Persistir los balances en **SQLite** en lugar de subirlos cada vez.
- Ampliar el catálogo de **indicadores** (liquidez, calidad de cartera, eficiencia).
- Comparar entidades entre sí (benchmark del sector).
