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
  agrupaciones.py      # Catálogo de agrupaciones PUC (portado de analisis_tasas)
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
  test_agrupaciones.py # Catálogo de agrupaciones + indicadores a 6 dígitos
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
`saldos_6dig` (1467×217, cuentas del catálogo de agrupaciones) ·
`riesgo_cartera` (21×5) · `var_factores` (21) · `var_correlacion` (19).

### Metodología de indicadores
- Los 8 indicadores básicos (`agregar_indicadores`) usan las cuentas principales.
- Los 17 indicadores avanzados (`indicadores_6dig`) usan **`src/agrupaciones.py`**:
  catálogo de agrupaciones PUC **portado del proyecto `analisis_tasas`**
  (`financiero/agrupaciones.py`), donde estas fórmulas están verificadas.
  Calidad por riesgo, coberturas, fondeos sobre cartera, capital institucional,
  activos improductivos, eficiencia operativa, márgenes y mezcla por modalidad.
- No se portaron los indicadores que requieren datos internos de cada
  cooperativa (raw_cartera, mart_solvencia, IRL, series mensuales): mora por
  días, duración/maduración, concentración top-20, solvencia regulatoria,
  ROA/ROE rolling 12M. Decisión del usuario 2026-06-10: no son necesarios aquí.

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

### Auto-deploy por webhook
- **Cada `git push` a `main` despliega solo en el servidor** (sin pasos manuales).
- Receptor: servicio **`webhook-sector.service`** (binario `/usr/bin/webhook`,
  paquete apt) en el puerto **9000**, config en `/etc/webhook.conf`
  (verifica firma HMAC-SHA256 y que la rama sea `main`).
- Acción: ejecuta `/opt/sector-solidario/deploy.sh` → `git pull` +
  `pip install -r requirements.txt` + `systemctl restart sector_solidario`.
  Log de despliegues: `/var/log/sector-solidario-deploy.log`.
- Lado GitHub: webhook id `639150646` (Settings → Webhooks del repo); el secreto
  HMAC está en `/etc/webhook.conf` del servidor (no se documenta aquí).
- **OJO:** existe otro servicio systemd llamado `webhook.service` que es del
  proyecto anterior (`analisis_tasas`, webhook.py propio en puerto 8080).
  **No tocarlo.** Su unit systemd falla al arrancar (puerto ocupado por un
  proceso suelto que es el que realmente atiende), pero así estaba y funciona.

## 7. Cómo actualizar

- **Cambio de código:** editar → `git push`. Eso es todo: CI corre los tests y
  el webhook despliega solo en el servidor (~30 s).
- **Datos de un mes nuevo:** poner los Excel en `data/raw/` local → `python -m src.etl`
  (regenera los parquet) → `git add data/processed && git commit && git push` →
  el webhook despliega solo.
- El deploy.sh ya instala dependencias nuevas (`pip install -r requirements.txt`).

## 8. Estado actual / pendientes

- [x] ETL consolidando los 6 reportes.
- [x] App multi-página (5 páginas) verificada con capturas reales.
- [x] Tests (9) en verde, local y en CI.
- [x] Repo público en GitHub + GitHub Actions.
- [x] Parquet procesados versionados (para despliegue en la nube).
- [x] **Desplegada en el servidor Hetzner** (systemd, puerto 8502). Se descartó
      Streamlit Community Cloud en favor del servidor propio.
- [ ] **Dominio + HTTPS** — pospuesto hasta que el usuario defina el dominio.
      Plan acordado: Caddy como proxy en 80/443 (certificado automático) →
      `localhost:8502` (y opcionalmente el 8501 del otro proyecto). Puertos
      80/443 libres en el servidor. Opciones de dominio discutidas: comprar
      uno (~USD 10/año), usar uno existente, DuckDNS (gratis) o sslip.io
      (gratis, sin registro).
- [x] **Auto-deploy por webhook** (push a `main` → deploy automático).
- [x] **Detalle a 6 dígitos integrado**: catálogo de agrupaciones + 17
      indicadores avanzados en Explorador y Comparador.
- [ ] (Idea futura) Mapa coroplético por departamento; página de alertas; export PDF.
- [ ] (Idea futura) Actualización automática de datos vía Action programada.

## 9. Convenciones

- Todo en español (UI, comentarios, mensajes de commit).
- Cifras COP compactas: **B** = billones (10¹²), **mM** = miles de millones, **M** = millones.
- Indicadores en `src/analytics.py`, protegidos contra división por cero (devuelven NaN).
- Mensajes de commit terminan con `Co-Authored-By: Claude <modelo> <noreply@anthropic.com>`
  (el modelo que haga el cambio; hasta junio 2026: Opus 4.8 y Fable 5).

---

## 10. Bitácora de cambios

> Añadir aquí una entrada por cada cambio relevante (más reciente arriba).

- **2026-06-13** — **Pestaña "Sector"** en el Panorama CAC (`views/panorama.py`,
  índice 2, tras "Principales cifras"). Tres bloques: (1) **gráfico por
  categoría** regulatoria con X fijo Plena→Intermedia→Básica y selector de hasta
  dos métricas (Activo/Pasivo/Patrimonio/Cartera bruta/Depósitos/Aportes/Nº
  asociados/Nº entidades) en **barras agrupadas** (offsetgroup + barmode group);
  los ejes se asignan **por tipo de métrica**: las cifras financieras comparten
  escala (mM) y van al eje principal, y los conteos (asociados/entidades) al eje
  secundario, que solo se activa si se elige un conteo (si solo hay conteos, el
  1º ocupa el principal);
  (2) **gráfico por departamento** (barras horizontales, **todos** los deptos
  con scroll vertical dentro de un `st.container(height=480)`, ordenados por la
  métrica principal, con la secundaria en eje X superior) — va **en la misma
  fila** que el (1) vía `st.columns(2)`; depende de las mismas métricas;
  (3) **tabla de entidades** (Entidad/Sigla/
  Asociados/Activos) con selector "Ver" (Todas o por subcategoría) y orden por
  Activos o Nº de asociados, con columna de ranking. Nueva función
  `analytics.agrupaciones_entidad` (aplica el catálogo PUC **por entidad** en un
  corte) para obtener Cartera bruta y Aportes por entidad; el resto de métricas
  salen de la foto. Los montos se muestran en **miles de millones (mM)**:
  valores /1e9 y ticks con formato plano (sin la "T"/SI de billones); los
  conteos no se escalan. Tests 27/27.

- **2026-06-13** — **Principales cifras: Activo/Pasivo/Patrimonio**. En la
  pestaña "Principales cifras" del Panorama CAC se añade la sección "Activo,
  Pasivo y Patrimonio" con tres métricas (total + variación 12M) y dos gráficas:
  barras agrupadas por **cierre de año** (diciembres del histórico + el corte
  seleccionado si no es diciembre, etiquetado p.ej. "2026·abr") y líneas
  **trimestrales** (marzo/junio/sep/dic). Nuevo helper `_etiqueta_periodo` en
  `views/panorama.py`. Respeta filtros y fecha de corte. Tests 27/27.

- **2026-06-13** — **Subcategoría + clasificación FIJA**. La categoría ya **no
  se recalcula con el corte visualizado**: se clasifica una sola vez con los
  activos del período de referencia `analytics.CATEGORIA_REF_PERIODO` ("2024-12",
  acorde al Parágrafo 1 del Art. 2.11.13.1.2) y se actualiza por código cuando
  la Supersolidaria reclasifique. Entidades que entraron después usan su primer
  período (JURISCOOP Intermedia-G1, COMUNA Básica-G2, CODELCAUCA Básica-G3).
  Nuevas funciones `subcategoria_cac` (Básica G1/G2/G3 = tercios del tope;
  Intermedia G1/G2 = punto medio ~$323 mM; Plena sin dividir), `activos_referencia`,
  `clasificar_cac`; `data.clasificacion_cac()` cacheada. Filtro **Subcategoría**
  en cascada desde Categoría. Reparto dic-2024: Básica 133 (G3=85), Intermedia
  43, Plena 8. Tests 26/26. **Enfoque manual confirmado** (usuario, 2026-06-13):
  la reclasificación oficial exige 3 cierres anuales consecutivos cruzando el
  umbral (no se automatiza; requeriría la UVR de cada 31-dic). Se añade hook
  `CATEGORIA_OVERRIDES` para forzar la categoría de entidades puntuales tras una
  reclasificación. Ej.: COAGROSUR (4458) sigue Básica-G1 (dic-2024 $116.6 mM);
  cruzó el tope por primera vez en dic-2025, así que no se reclasificaría pronto.

- **2026-06-13** — **Filtros del Panorama CAC**: se quita "Tipo de CAC" y se
  agregan **Municipio** (depende del departamento elegido) y **Categoría**
  regulatoria (Básica/Intermedia/Plena, Art. 2.11.13.1.2). Nueva función
  `analytics.categoria_cac` con umbrales en UVR (315M y 1.400M) × UVR dic-2024
  (376.7763) → cortes en pesos $118.684.534.500 y $527.486.820.000. Tests 24/24.

- **2026-06-13** — **Panorama CAC ampliado con cartera/riesgo/rentabilidad**
  (6 pestañas). Nuevas funciones en analytics que aplican el catálogo de
  agrupaciones (`agrupaciones.py`) al **panel mensual** del histórico:
  `panel_mensual` (PERIODO×CUENTA, **rellena NaN con 0** para que las
  agrupaciones escalares no se contaminen), `serie_alias`, `valor_alias`,
  `ratio_alias`, `roa_roe` (anualiza el excedente acumulado dividiendo por
  meses corridos). `data.historico_panel()` cachea el panel del sector.
  Pestañas: Principales cifras · Balance (composición activo/patrimonio +
  evolución + por depto/tipo) · Cartera (modalidad + calidad/cobertura
  mensual, validado: bruta $20.4 B, calidad 8.5%, cobertura 90.3%) ·
  Depósitos y fondeo (por tipo: CDAT $10 B, vista $3.7 B; depósitos/cartera
  69%) · Rentabilidad (ROA/ROE anualizados, margen, eficiencia) · Glosario.
  Tests 23/23. Verificado en navegador.

- **2026-06-13** — **Panorama CAC rediseñado al estilo "Principales cifras"**
  (tablero Superfinanciera). `views/panorama.py`: **selector de fecha de corte**
  (cualquiera de los 100 meses del histórico → recalcula todo vía `foto_cac`),
  **4 pestañas** (`st.tabs`): Principales cifras (KPIs destacados de color +
  grid con variación 12M), Activo·Pasivo (evolución de balance + activos por
  depto + torta especializadas/multiactivas), Indicadores (profundización con
  **ratios internos** Cartera/Activo, Depósitos/Activo, Solvencia + evolución +
  concentración Top 10/25/50 + ranking) y Glosario. Sin PIB (decisión del
  usuario: ratios internos). Verificado en navegador. Tests 19/19.

- **2026-06-12** — **Reforma Panorama → 📈 Panorama CAC** (`views/panorama.py`):
  universo solo CAC. Cifras financieras desde el histórico mensual (último
  corte, con variación 12M en los KPIs vía `analytics.foto_cac` +
  `serie_historica`); del reporte de cuentas principales solo se usa
  ASOCIADOS y metadatos de identificación (nombre, sigla, depto, tipo).
  Filtros: departamento y tipo de CAC. Torta especializadas vs. multiactivas,
  concentración Top 10/25/50. Tests 19/19. Pendiente reformar las otras
  4 páginas al universo CAC.

- **2026-06-12** — **Página 📜 Histórico CAC** (`views/historico.py`): series
  mensuales 2018-2026 por entidad o sector (KPIs con variación 12M, cuentas a
  elegir del catálogo completo, rango de años, tabla). Las fusiones del censo
  de novedades se anotan como líneas punteadas en las series (EVENTOS por
  código de entidad; verificado con Coovitel: 4 saltos = 4 fusiones).
  Funciones nuevas en analytics (`serie_historica`, `entidades_por_periodo`,
  `variacion_anual`) + loaders en data.py. Tests 18/18.
  **Arreglos al ETL histórico:** (1) enero 2020 venía con los valores corridos
  una fila respecto a las etiquetas (creaba ~97 cuentas fantasma y activo=0;
  se detecta por la fila 100000 vacía y se realinea validando A=P+Pt);
  (2) reparación de codificación: \x90 espurio en las "É" y "??" por "Ñ";
  (3) validación final A=P+Pt en los 100 períodos (falla ruidosamente).
  **Censo de novedades completo** en `NOVEDADES COOPERATIVAS CAC 2018-2026.xlsx`:
  15 salidas (fusiones: 4 a Coovitel, Utrahuilca, Cootracerrejón, Cooindegabo,
  Conecta, Juriscoop; liquidaciones: El Progreso Social, Pilotos Civiles),
  3 entradas (transformación a CAC especializada: Juriscoop, Comuna,
  Codelcauca) y 4 atrasos (Coagrupo, Soycoop, Avancop, Colgate).

- **2026-06-12** — **Histórico mensual CAC 2018-01 → 2026-04:** el usuario
  descarga 100 Excel mensuales (carpeta `ESTADOS FINANCIEROS COOPERATIVAS DE
  AHORRO Y CREDITO/`, no versionada). Nuevo `src/etl_historico.py` que los
  consolida en formato largo → `data/processed/historico_cac.parquet`
  (5.37 M filas, 100 períodos, 184 entidades, 1.625 cuentas a 6 dígitos,
  ~37 MB) + catálogos `historico_cuentas.parquet` y `historico_entidades.parquet`.
  Particularidades manejadas: layouts cambiantes por época (filas de encabezado
  localizadas dinámicamente, fila NIT sin rótulo desde 2026, `.xls` con xlrd —
  **nueva dependencia `xlrd`**), cuenta 100000 duplicada en mayo 2021 (se toma
  la última fila, que cuadra con P+Pt), transición de catálogo en dic-2025
  (1.244 cuentas extra ese mes). Validado: A=P+Pt en los 100 períodos,
  2026-04 idéntico a `cac_abril.parquet` (0 diferencias en 56.709 saldos).
  Decisión de alcance (2026-06-11): **el portal se enfoca solo en las CAC**
  (las demás entidades reportan con periodicidades variadas).

- **2026-06-10** — **Indicadores a 6 dígitos:** se porta el catálogo de
  agrupaciones PUC de `analisis_tasas` a `src/agrupaciones.py` (con versión
  vectorizada `calcular_df`). Nuevo paso de ETL `construir_saldos_6dig` que
  extrae del Excel de 95 MB las ~216 cuentas del catálogo →
  `saldos_6dig.parquet` (1467×217, ~0.7 MB, versionado). 17 indicadores nuevos
  en `analytics.indicadores_6dig` (calidad por riesgo, coberturas, fondeos,
  capital institucional, improductivos, eficiencia, márgenes, mezcla de
  cartera) integrados en Explorador (sección propia + torta de modalidades) y
  Comparador. Validado: activo 6dig = cuentas principales en las 1467
  entidades; mediana calidad CAC 6.6%. Tests 14/14 en verde.

- **2026-06-10** — **Auto-deploy:** webhook de GitHub (push a `main`) →
  `webhook-sector.service` (puerto 9000) ejecuta `deploy.sh` (pull + pip +
  restart). Verificado con ping 200 y push real. Se respetó intacto el
  `webhook.service` del proyecto anterior.
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
