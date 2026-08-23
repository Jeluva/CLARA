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
- **155 tests backend (pytest) + 25 frontend (vitest) = 180 tests** en verde.
- Métricas financieras verificadas a mano + test de integración sobre el seed.
- Endpoints documentados en Swagger (`/docs`).
- CI/CD con GitHub Actions (pytest + tsc + vitest).

## Fuentes de datos

- **Precios:** yfinance (datos reales). Mock disponible con `USE_MOCK_SOURCES=true`.
- **Noticias:** NewsAPI (requiere key). Fallback a fixtures con sentimiento VADER real.
- **Macro:** yfinance (índices, US 10Y) + dolarapi.com (dólar). Riesgo país y
  BADLAR estáticos.
- **Transcripciones:** yt-dlp + youtube-transcript-api reales contra los
  canales seguidos, con mock de fallback. En prod, YouTube bloquea las IPs
  de datacenter de Render — workaround gratis vía
  `POST /api/transcripts/ingest-external` + `scripts/fetch_transcripts_local.py`
  (corrido desde una IP residencial), o pago vía proxy Webshare
  (`WEBSHARE_PROXY_USERNAME/PASSWORD`). Ver fase-12.

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

## V2 completado

- ~~Sentimiento en español con LLM~~ ✓ detección de idioma + Groq/Qwen (ADR 0005).
- ~~Serie de P&L realizada~~ ✓ respeta `opened_at`, toggle Basket/Realizado (ADR 0003).
- ~~Riesgo país y BADLAR~~ ✓ argentinadatos.com.
- ~~Comparador de activos~~ ✓ métricas lado a lado en Research.
- ~~Serie temporal de sentimiento~~ ✓ chart con tendencia en Noticias.

## Pendiente opcional

- Si se quiere automatizar transcripciones sin intervención manual: contratar
  el plan Residential de Webshare (el gratuito de datacenter no sirve, ya
  probado) y cargar las credenciales en Render.

## Cómo quedó para revisar

- Corre con dos comandos; Postgres opcional vía `docker compose up -d`.
- Historia contada: README narrativo, una entrada de devlog por fase y 5 ADRs.
- Commits atómicos y descriptivos, uno por fase, pensados como materia prima
  para el contenido de "building in public".
