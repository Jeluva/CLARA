# Fase 10 — Datos reales: yfinance, NewsAPI, dolarapi

## El problema que resolvía

Hasta acá toda la ingestión usaba mocks determinísticos. Para portfolio
profesional eso está bien documentado, pero enchufar fuentes reales demuestra
que la arquitectura medallion no era un ejercicio académico — el pipeline
`fetch → bronze → validar → promover` funciona igual con datos de verdad.

## Lo que se hizo

**Precios reales con yfinance.** El módulo de ingestión de precios ahora baja
datos históricos reales. El flujo bronze → quality check → silver no cambió;
solo se reemplazó el paso de fetch.

**Noticias reales con NewsAPI.** Se conectó el cliente de noticias a la API de
NewsAPI (requiere key gratuita). Las noticias pasan por el mismo pipeline de
sentimiento VADER antes de promoverse a silver.

**Macro real.** Los índices (S&P 500, Nasdaq 100, Merval) se obtienen de
yfinance; el dólar MEP/CCL/Blue de dolarapi.com (API pública sin key). Riesgo
país y BADLAR mantienen valores estáticos por falta de fuente gratuita
machine-readable.

## Decisiones

- `USE_MOCK_SOURCES` en `.env` permite volver a mocks sin tocar código.
- Cada fetcher real tiene fallback al mock correspondiente si la fuente falla.
- Las API keys van en `.env` con `.env.example` documentado.
