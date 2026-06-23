# RESUMEN — CLARA, de carpeta vacía a mesa de análisis

Bitácora de cierre. Qué quedó construido, qué decisiones se tomaron y qué sigue.

## Qué quedó construido y funcionando

Una app full-stack que corre de punta a punta con dos comandos (`uvicorn` +
`npm run dev`), con las **cinco pestañas completas**, datos reales enchufados
y un chatbot IA multi-provider:

- **Portfolio** — valor total y P&L (total/diario), tabla de posiciones con
  P&L y peso (clickeables → detalle de activo con chatbot), evolución acumulada
  vs. benchmark (SPY), panel de riesgo (volatilidad, drawdown, Sharpe, beta,
  concentración top-3 y Herfindahl) y donuts de exposición por sector/país/moneda.
- **Noticias & Sentimiento** — feed filtrable por activo con tag de sentimiento
  coloreado, score agregado por ticker y transcripciones resumidas. Sentimiento
  **calculado con VADER**, no hardcodeado.
- **Research** — matriz de correlación (heatmap), indicadores técnicos (SMA
  20/50, RSI 14, MACD) por activo, y **comparador de activos** con métricas
  lado a lado.
- **Macro** — índices (yfinance), dólar MEP/CCL/Blue (dolarapi.com), tasas.
- **Ingreso de datos** — CRUD de activos, posiciones y transacciones; botón de
  forzar ingestión por fuente (precios, noticias, transcripciones) con feedback.
- **Chatbot IA** — análisis fundamental por activo con contexto real del
  portfolio. Cadena multi-provider: Groq → Qwen → Gemini → Anthropic → estático.

### Criterios de aceptación cumplidos
- `alembic upgrade head` crea el esquema medallion; el seed deja un portfolio de
  ejemplo + ~1 año de precios + noticias + transcripciones, 0 en cuarentena.
- **80 tests backend (pytest) + 7 frontend (vitest)** en verde.
- Métricas financieras verificadas a mano + test de integración sobre el seed.
- Endpoints documentados en Swagger (`/docs`).
- CI/CD con GitHub Actions (pytest + tsc + vitest).

## Fuentes de datos

- **Precios:** yfinance (datos reales). Mock disponible con `USE_MOCK_SOURCES=true`.
- **Noticias:** NewsAPI (requiere key). Fallback a fixtures con sentimiento VADER real.
- **Macro:** yfinance (índices, US 10Y) + dolarapi.com (dólar). Riesgo país y
  BADLAR estáticos.
- **Transcripciones:** mock determinístico (youtube-transcript-api listo).

Todas las fuentes siguen `fetch → bronze → validar → promover`. El scheduler
(APScheduler) tiene los jobs registrados con su cron; apagado por defecto
(`SCHEDULER_ENABLED=false`).

## Decisiones de arquitectura (ADRs)

1. **0001** — FastAPI + medallion para datos financieros.
2. **0002** — Cuarentena de data quality en vez de descarte silencioso.
3. **0003** — `portfolio_value_series` con shares constantes (backtest del
   basket); la serie de P&L realizada queda como V2.
4. **0004** — Convenciones de anualización (252) y definición de Sharpe.
5. **0005** — Sentimiento: VADER para inglés, LLM para español (V2).

## Próximos pasos sugeridos (V2)

- Sentimiento en español con un LLM (ADR 0005).
- Serie de P&L **realizada** que respete `opened_at` y las transacciones, para
  separar performance del basket de performance de las decisiones de timing
  (ADR 0003).
- Transcripciones reales con youtube-transcript-api.
- Riesgo país y BADLAR con fuente machine-readable (BCRA API / Ámbito).
- Capturas finales en `docs/screenshots/` para el README.

## Cómo quedó para revisar

- Corre con dos comandos; Postgres opcional vía `docker compose up -d`.
- Historia contada: README narrativo, una entrada de devlog por fase y 5 ADRs.
- Commits atómicos y descriptivos, uno por fase, pensados como materia prima
  para el contenido de "building in public".
