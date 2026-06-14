# RESUMEN — CLARA, de carpeta vacía a mesa de análisis

Bitácora de cierre del run autónomo. Qué quedó construido, qué es mock, qué
decisiones se tomaron y qué sigue.

## Qué quedó construido y funcionando

Una app full-stack que corre de punta a punta con dos comandos (`uvicorn` +
`npm run dev`), con las **cinco pestañas completas** y datos reales del seed:

- **Portfolio** — valor total y P&L (total/diario), tabla de posiciones con
  P&L y peso, evolución acumulada vs. benchmark (SPY), panel de riesgo
  (volatilidad, drawdown, Sharpe, beta, concentración top-3 y Herfindahl) y
  donuts de exposición por sector/país/moneda.
- **Noticias & Sentimiento** — feed filtrable por activo con tag de sentimiento
  coloreado, score agregado por ticker y transcripciones resumidas. Sentimiento
  **calculado con VADER**, no hardcodeado.
- **Research** — matriz de correlación (heatmap) e indicadores técnicos (SMA
  20/50, RSI 14) por activo.
- **Macro** — índices, dólar MEP/CCL/blue, riesgo país y tasas (mock declarado).
- **Ingreso de datos** — alta/baja de activos y posiciones end-to-end (cargás y
  aparece en Portfolio) y botón de forzar ingestión por fuente.

### Criterios de aceptación cumplidos
- `alembic upgrade head` crea el esquema medallion; el seed deja un portfolio de
  ejemplo + ~1 año de precios + noticias + transcripciones, 0 en cuarentena.
- **73 tests backend (pytest) + 7 frontend (vitest)** en verde.
- Métricas financieras verificadas a mano + test de integración sobre el seed.
- Endpoints documentados en Swagger (`/docs`).

## Qué quedó mockeado y por qué

AUTORUN prohíbe llamadas reales a la red en este run, así que **toda la ingestión
usa mocks determinísticos**, documentados:

- **Precios:** GBM con semilla fija por ticker (reproducible).
- **Noticias/transcripciones:** fixtures en inglés con sentimiento VADER real.
- **Macro:** valores realistas pero estáticos.

Todas las fuentes siguen `fetch → bronze → validar → promover`: enchufar la
fuente real es reemplazar solo el `fetch`. El scheduler (APScheduler) ya tiene
los jobs registrados con su cron; está apagado por defecto
(`SCHEDULER_ENABLED=false`).

## Decisiones de arquitectura (ADRs)

1. **0001** — FastAPI + medallion para datos financieros.
2. **0002** — Cuarentena de data quality en vez de descarte silencioso.
3. **0003** — `portfolio_value_series` con shares constantes (backtest del
   basket); la serie de P&L realizada queda como V2.
4. **0004** — Convenciones de anualización (252) y definición de Sharpe.
5. **0005** — Sentimiento: VADER para inglés, LLM para español (V2).

## Próximos pasos sugeridos

- Enchufar fuentes reales (yfinance, News API, `youtube-transcript-api`,
  dolarapi) reemplazando el paso de fetch de cada cliente.
- Sentimiento en español con un LLM (ADR 0005).
- Serie de P&L **realizada** que respete `opened_at` y las transacciones, para
  separar performance del basket de performance de las decisiones de timing
  (ADR 0003).
- Correlaciones e indicadores sobre precios reales (con mock dan ~0 por ser
  random walks independientes).
- Capturas finales en `docs/screenshots/` para el README y el contenido.

## Cómo quedó para revisar

- Corre con dos comandos; Postgres opcional vía `docker compose up -d`.
- Historia contada: README narrativo, una entrada de devlog por fase y 5 ADRs.
- Commits atómicos y descriptivos, uno por fase, pensados como materia prima
  para el contenido de "building in public".
