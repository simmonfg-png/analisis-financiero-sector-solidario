# CLAUDE.md — Contexto del proyecto

> **Propósito de este archivo:** memoria viva del proyecto. Claude lo lee al
> iniciar cada sesión para saber **todo lo que se ha hecho**. 
> **REGLA:** ante cualquier cambio relevante (código, datos, despliegue,
> decisiones), añadir una entrada en la **Bitácora de cambios** al final.

---

## 1. Qué es el proyecto

Portal web (**Streamlit**) para analizar la situación financiera de las entidades
del **sector solidario colombiano**, a partir de los reportes oficiales de la
**Superintendencia de Economía Solidaria (Supersolidaria)**.

- **Corte de datos:** 31 de marzo de 2026 (cooperativas de ahorro y crédito: 30 de abril de 2026).
- **Idioma del proyecto y la comunicación:** español.
- **Usuario/propietario:** simmonfg-png (simmonfg@gmail.com).

## 2. Stack y entorno

- Python 3.12 · Streamlit 1.57.0 · pandas 3.0.3 · plotly 6.7.0 · openpyxl 3.1.5 · pyarrow 24.0.0 · pytest.
- SO de trabajo: **Windows** (PowerShell). Ruta local del proyecto:
  `C:\Users\SIMON\Desktop\PROYECTOS\ANALISIS FINANCIERO SECTOR SOLIDARIO`.
- Arrancar la app: `streamlit run app.py` (abre en http://localhost:8501).
- `gh` (GitHub CLI) instalado en `C:\Program Files\GitHub CLI\gh.exe`,
  autenticado como `simmonfg-png` con scopes `repo` y `workflow`.

## 3. GitHub

- **Repo (público):** https://github.com/simmonfg-png/analisis-financiero-sector-solidario
- Rama principal: `main`.
- **CI:** GitHub Actions (`.github/workflows/tests.yml`) corre `pytest` en cada push/PR.
- **Identidad git configurada:** `simmonfg-png <simmonfg@gmail.com>`.

## 4. Arquitectura

```
app.py                 # Navegación multi-página (st.navigation)
config.py              # Dominio: catálogo PUC, rutas, archivos fuente
src/
  etl.py               # Pipeline: lee los Excel de data/raw/ → parquet en data/processed/
  data.py              # Acceso cacheado a los parquet (st.cache_data); corre ETL si faltan
  analytics.py         # Indicadores vectorizados y agregados (sector/entidad)
  format.py            # Formateo de cifras COP (pesos, %, cantidades compactas)
  indicators.py        # (Legado) indicadores de un balance suelto — lógica pura
  loader.py, charts.py # (Legado del scaffold inicial)
views/
  panorama.py          # 📈 KPIs macro, concentración, activos por tipo/depto, rankings
  explorador.py        # 🔍 Ficha por entidad: balance, resultados, indicadores vs. mediana
  ahorro_credito.py    # 💰 Tasas activa/pasiva, margen, segmentos, modalidades
  riesgo.py            # ⚠️ Indicador de cartera vs. umbrales σ + factores/correlación VaR
  comparador.py        # ⚖️ Benchmark de varias entidades (tabla + radar)
tests/
  test_indicators.py   # Lógica pura (scaffold)
  test_analytics.py    # Analítica a nivel sector/entidad
data/
  raw/                 # Excel originales (IGNORADOS en git, incl. uno de 95 MB)
  processed/           # Parquet consolidados (~1.2 MB, SÍ versionados)
.claude/launch.json    # Config para previsualizar la app (puerto 8533)
```

## 5. Datos fuente (6 reportes de la Supersolidaria)

Van en `data/raw/` (no se versionan; el ETL los procesa). Son **datos públicos**.

| Archivo (en data/raw/) | Contenido | Formato |
|---|---|---|
| `…cuentas_principales_marzo_2026.xlsx` | 1.467 entidades + cuentas principales | tabla ancha |
| `…6dig_marzo_2026.xlsx` (95 MB) | Plan de cuentas a 6 dígitos, todas las entidades | largo, 5 hojas |
| `…ahorro_credito_abril.xlsx` | Estados financieros CAC (abril) | transpuesto |
| `…tasas__deleg_finan_marzo.xlsx` | Tasas activas/pasivas ponderadas (172 ent.) | tabla |
| `…desviacion_estandar_marzo_2026.xlsx` | Serie del indicador de cartera (σ) | serie |
| `…var_mar_26.xlsx` | Factores y correlaciones para VaR | 3 hojas |

**Llave común para cruzar archivos:** `CODIGO ENTIDAD`.

### Tablas procesadas (data/processed/*.parquet)
`entidades` (1467×62) · `tasas` (172×15) · `cac_abril` (56.709×4) ·
`riesgo_cartera` (21×5) · `var_factores` (21) · `var_correlacion` (19).

### Cifras de referencia del sector (marzo 2026)
Activos **$61.8 B** · Pasivos $38.8 B · Patrimonio **$23.0 B** ·
Asociados **7.03 M** · Entidades 1.467. Mayor entidad: Coomeva ($6.5 B).

## 6. Despliegue (servidor Hetzner)

La app está **desplegada en el servidor Hetzner del usuario** (Ubuntu 24.04,
4 GB RAM; la IP no se documenta aquí por ser repo público — el usuario la conoce).

- Ruta en el servidor: `/opt/sector-solidario` (clon del repo de GitHub).
- Entorno: `venv` propio (`/opt/sector-solidario/venv`).
- Servicio systemd: **`sector_solidario.service`** → puerto **8502**
  (`--server.address 0.0.0.0`), arranque automático y `Restart=always`.
- Convive con otro proyecto Streamlit del usuario: `analisis_tasas.service`
  en el puerto 8501 (no tocar). Sin Docker, sin nginx, sin firewall de Hetzner.
- Acceso: `http://IP_DEL_SERVIDOR:8502` (HTTP sin dominio/HTTPS por ahora).
- Comandos útiles en el servidor:
  `systemctl status|restart sector_solidario` · logs: `journalctl -u sector_solidario -f`.

## 7. Cómo actualizar

- **Cambio de código:** editar → `git push` (CI corre tests) → en el servidor:
  `cd /opt/sector-solidario && git pull && systemctl restart sector_solidario`.
- **Datos de un mes nuevo:** poner los Excel en `data/raw/` local → `python -m src.etl`
  (regenera los parquet) → `git add data/processed && git commit && git push` →
  mismo `git pull` + restart en el servidor.
- Si cambian las dependencias: además `./venv/bin/pip install -r requirements.txt`.

## 8. Estado actual / pendientes

- [x] ETL consolidando los 6 reportes.
- [x] App multi-página (5 páginas) verificada con capturas reales.
- [x] Tests (9) en verde, local y en CI.
- [x] Repo público en GitHub + GitHub Actions.
- [x] Parquet procesados versionados (para despliegue en la nube).
- [x] **Desplegada en el servidor Hetzner** (systemd, puerto 8502). Se descartó
      Streamlit Community Cloud en favor del servidor propio.
- [ ] (Idea futura) Dominio + HTTPS (p. ej. con Caddy) para ambas apps del servidor.
- [ ] (Idea futura) Auto-deploy: webhook o cron que haga `git pull` en el servidor.
- [ ] (Idea futura) Integrar el detalle a 6 dígitos en el Explorador.
- [ ] (Idea futura) Mapa coroplético por departamento; página de alertas; export PDF.
- [ ] (Idea futura) Actualización automática de datos vía Action programada.

## 9. Convenciones

- Todo en español (UI, comentarios, mensajes de commit).
- Cifras COP compactas: **B** = billones (10¹²), **mM** = miles de millones, **M** = millones.
- Indicadores en `src/analytics.py`, protegidos contra división por cero (devuelven NaN).
- Mensajes de commit terminan con `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## 10. Bitácora de cambios

> Añadir aquí una entrada por cada cambio relevante (más reciente arriba).

- **2026-06-10** — **Despliegue en Hetzner:** se clona el repo en
  `/opt/sector-solidario`, venv + requirements, y servicio systemd
  `sector_solidario.service` en el puerto 8502 (enabled + Restart=always).
  Convive con `analisis_tasas.service` (8501). Acceso por `http://IP:8502`.
- **2026-06-09** — Se crea este `CLAUDE.md` como memoria del proyecto.
- **2026-06-09** — Datos: se versionan los parquet procesados (~1.2 MB) en
  `data/processed/` para el despliegue en la nube; los Excel crudos siguen ignorados.
- **2026-06-09** — CI: se añade GitHub Actions (`.github/workflows/tests.yml`) que
  corre `pytest` en cada push/PR. Primera ejecución en verde.
- **2026-06-09** — Se publica el proyecto en GitHub (repo público) e se instala/
  autentica `gh`. Identidad git: simmonfg-png.
- **2026-06-09** — Se construye el portal: ETL (`src/etl.py`), capa de datos
  (`src/data.py`), analítica (`src/analytics.py`), formateo (`src/format.py`),
  5 páginas en `views/`, y `test_analytics.py`. Se reescribe `app.py` a
  navegación multi-página y se amplía `config.py` con el catálogo PUC.
- **2026-06-09** — Punto de partida: scaffold inicial de Streamlit (carga de un
  balance suelto). Se reciben los 6 reportes de la Supersolidaria.
