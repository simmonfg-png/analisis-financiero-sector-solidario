# Análisis Financiero del Sector Solidario

Portal web (Streamlit) para analizar la situación financiera de las entidades
del sector solidario colombiano a partir de los reportes publicados por la
**Superintendencia de Economía Solidaria**. Consolida varios reportes oficiales
en un dataset limpio y los explora mediante un dashboard multi-página.

Corte de los datos: **31 de marzo de 2026** (cooperativas de ahorro y crédito a
**30 de abril de 2026**).

## Páginas

- **📈 Panorama del sector** — KPIs macro, concentración de activos, composición
  por tipo de entidad y por departamento, rankings.
- **🔍 Explorador de entidades** — ficha financiera por entidad: datos básicos,
  estructura de balance, estado de resultados e indicadores comparados con la
  mediana de su tipo.
- **💰 Ahorro y crédito** — tasas activas/pasivas ponderadas, margen de
  intermediación y análisis por segmento y modalidad.
- **⚠️ Riesgo y supervisión** — indicador de cartera frente a umbrales σ (alerta)
  y factores/correlaciones del cálculo de VaR de mercado.
- **⚖️ Comparador** — benchmark lado a lado de varias entidades (tabla + radar).

## Estructura

```
ANALISIS FINANCIERO SECTOR SOLIDARIO/
├── app.py                 # Punto de entrada y navegación multi-página
├── config.py              # Dominio: catálogo PUC, rutas y archivos fuente
├── requirements.txt
├── data/
│   ├── raw/               # Excel originales de la Supersolidaria (ignorado en git)
│   └── processed/         # Tablas consolidadas en parquet (generadas; ignorado)
├── src/
│   ├── etl.py             # Pipeline: lee los Excel → parquet limpios
│   ├── data.py            # Acceso cacheado a los parquet (Streamlit)
│   ├── analytics.py       # Indicadores y agregados a nivel sector/entidad
│   ├── format.py          # Formateo de cifras (pesos, porcentajes)
│   ├── indicators.py      # Indicadores de un balance suelto (lógica pura)
│   ├── loader.py / charts.py
├── views/                 # Una página por módulo (panorama, explorador, …)
└── tests/                 # pytest (test_indicators.py, test_analytics.py)
```

## Reportes fuente

Colocar los Excel originales en `data/raw/` (la app ejecuta el ETL la primera vez):

| Archivo | Contenido |
|---|---|
| `…cuentas_principales_marzo_2026.xlsx` | 1.467 entidades + cuentas principales |
| `…6dig_marzo_2026.xlsx` | Plan de cuentas a 6 dígitos (detalle) |
| `…ahorro_credito_abril.xlsx` | Estados financieros CAC (abril) |
| `…tasas__deleg_finan_marzo.xlsx` | Tasas activas/pasivas ponderadas |
| `…desviacion_estandar_marzo_2026.xlsx` | Serie del indicador de cartera (σ) |
| `…var_mar_26.xlsx` | Factores y correlaciones para VaR |

## Puesta en marcha (Windows / PowerShell)

```powershell
# 1. Entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Dependencias
pip install -r requirements.txt

# 3. (Opcional) generar el dataset consolidado manualmente
python -m src.etl

# 4. Arrancar el portal
streamlit run app.py
```

La app abre en el navegador (http://localhost:8501).

## Tests

```powershell
pytest
```

## Próximos pasos sugeridos

- Incorporar el **detalle a 6 dígitos** en el Explorador (balance completo por
  entidad), leyendo el parquet bajo demanda.
- Soportar **varios períodos** para ver evolución y variaciones mes a mes.
- **Mapa** coroplético de activos/asociados por departamento.
- Exportar **fichas en PDF/Excel** por entidad y descargas de las tablas.
- Página de **alertas**: entidades fuera de rango (σ), solvencia baja, etc.
