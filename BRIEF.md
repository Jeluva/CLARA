# BRIEF — CLARA: Plataforma de análisis de portfolio

## Rol y objetivo
Actuá como un ingeniero de software full-stack senior con experiencia en data
engineering y en aplicaciones financieras. Vamos a construir CLARA, una
plataforma local de análisis de cartera de inversión que cruza posiciones con
noticias, sentimiento, datos macro y transcripciones de YouTube. El proyecto se
va a publicar como pieza de portfolio profesional, así que la calidad de código,
la arquitectura y el diseño visual importan tanto como la funcionalidad.

## Principios no negociables
- Código limpio, tipado y testeado. Funciones de cálculo financiero SIEMPRE con
  tests unitarios.
- Arquitectura por capas: ingestión → almacenamiento (medallion bronze/silver/
  gold) → API → frontend. No mezclar responsabilidades.
- Idempotencia en la ingestión: correr un job dos veces no duplica datos.
- Data quality: validar antes de promover de bronze a silver; los registros que
  fallan van a una tabla de cuarentena, nunca se descartan en silencio.
- Manejo de errores explícito en cada llamada a fuentes externas (timeouts,
  rate limits, respuestas vacías).
- Commits atómicos y descriptivos (vamos a documentar el proceso).
- NO hardcodear API keys: usar variables de entorno (.env, con .env.example).

## Stack
- Backend: Python 3.11+, FastAPI, SQLAlchemy, Pydantic.
- DB: SQLite en dev (archivo local), Postgres-ready en prod (solo cambia el
  connection string). Migraciones con Alembic.
- Orquestación: APScheduler para jobs programados de ingestión.
- Datos/análisis: pandas, numpy. Sentimiento: VADER para inglés y un fallback
  configurable para español. Transcripciones: youtube-transcript-api.
- Frontend: React + Vite + TypeScript + Tailwind CSS + Recharts.
- Tests: pytest (backend), vitest (frontend).

## Diseño visual (obligatorio, dark/minimalista/iOS)
- Fondo #0D0D0F; cards #1C1C1E; separadores #2C2C2E.
- Texto primario #FFFFFF; secundario #8E8E93.
- Acento iOS Blue #0A84FF. Ganancia/positivo #30D158; pérdida/negativo #FF453A;
  alerta #FF9F0A.
- Tipografía Inter; números con tabular-nums.
- Navegación: sidebar vertical fija a la izquierda con íconos + label por pestaña.
- Cards con bordes redondeados (radius 12-16px), sombras sutiles, padding generoso.
- Transiciones 150-200ms. Sin decoración innecesaria. Densidad alta pero legible.

## Estructura del repo
/clara
  /backend
    /app
      /ingestion      # clients de fuentes (precios, noticias, youtube, macro)
      /storage        # modelos SQLAlchemy, capas bronze/silver/gold
      /analytics      # cálculo de métricas de portfolio y riesgo
      /quality        # checks de data quality + cuarentena
      /api            # routers FastAPI
      /scheduler      # jobs APScheduler
      main.py
    /tests
    .env.example
  /frontend
    /src
      /components     # componentes UI reutilizables (Card, Metric, Chart, etc.)
      /pages          # una por pestaña
      /lib            # cliente API, helpers de formato (moneda, %, fechas)
      /styles         # theme tokens (colores, tipografía)
    ...
  README.md
  docker-compose.yml  # postgres opcional para prod
  /docs
    /devlog           # bitácora de desarrollo (storytelling)

## Esquema de datos
assets(id, ticker, name, asset_class, sector, country, currency)
positions(id, asset_id, quantity, avg_cost, opened_at, status)
transactions(id, asset_id, type, quantity, price, fee, executed_at)
prices(id, asset_id, date, close, source, ingested_at)
news(id, asset_id, title, summary, url, source, sentiment, published_at, ingested_at)
transcripts(id, source_channel, video_id, title, url, transcript, summary, sentiment, published_at)
metrics_daily(id, snapshot_date, portfolio_value, daily_return, drawdown, sharpe, ...)
quarantine(id, source_table, raw_payload, failed_check, created_at)

## Pestañas (frontend)
1. PORTFOLIO (main): valor total, P&L total y diario, tabla de posiciones con
   precio actual / P&L / peso, gráfico de evolución vs. benchmark, donut de
   exposición por sector y por moneda, panel de métricas de riesgo
   (volatilidad, drawdown, Sharpe, beta, concentración).
2. NOTICIAS & SENTIMIENTO: feed de noticias por activo con tag de sentimiento
   (color), score de sentimiento agregado por ticker con tendencia, sección de
   transcripciones de YouTube resumidas con su sentimiento. Filtro por activo.
3. RESEARCH: matriz de correlación entre activos (heatmap), indicadores
   técnicos básicos (medias móviles, RSI) por activo seleccionado, comparador
   de activos.
4. MACRO: índices de referencia (S&P 500, Merval), dólar MEP/CCL, riesgo país,
   tasas — con su variación. Tarjetas tipo "ticker".
5. INGRESO DE DATOS: formularios para alta/edición de activos, posiciones y
   transacciones; gestión de las cuentas/canales de YouTube a seguir; botón de
   "forzar ingestión ahora" por fuente, con feedback de éxito/error.

## Métricas a implementar (con tests)
- Rendimiento total y por activo; rendimiento acumulado; time-weighted return.
- Volatilidad anualizada, max drawdown, Sharpe ratio, beta vs. benchmark.
- Exposición por sector / país / moneda; concentración (top-3, Herfindahl).
- Score de sentimiento por ticker (-1 a 1) y su serie temporal.
- Matriz de correlación entre activos.

## Reglas de ingestión
- Cada fuente es un módulo independiente con la misma interfaz: fetch() ->
  guarda en bronze -> valida -> promueve a silver.
- Jobs programados (APScheduler): precios cada cierre de mercado; noticias cada
  N horas; transcripciones diariamente. Todos con retry y logging.
- Si una fuente externa requiere API key que no tengo, dejá el módulo con un
  mock realista y documentá en el README cómo enchufar la key real.

## Entregables de cada fase
Al terminar una fase: que la app corra, los tests pasen, y un resumen corto de
qué se hizo y qué decisiones se tomaron (para la bitácora de devlog).
