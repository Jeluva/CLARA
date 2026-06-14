# Fase 6 — Plan: Noticias & Sentimiento

## Objetivo
Ingestión (mock) de noticias y transcripciones de YouTube con sentimiento, y la
pestaña que muestra el feed por activo, el score agregado por ticker y las
transcripciones resumidas.

## Decisiones
- **Sentimiento real, no hardcodeado:** uso VADER sobre titulares en inglés
  (plausible para CEDEARs/US tickers), que devuelve un compound en [-1, 1]. Para
  español financiero, VADER es flojo → documentado en ADR que el camino real es
  un LLM (V2). No construyo un VADER-en-español a medias.
- Las fuentes son mock determinísticas (sin red, AUTORUN). Mismo patrón:
  fetch → bronze → validar → promover.
- El score por ticker es el promedio de sentimientos de sus noticias.

## Archivos
- `ingestion/sentiment.py`: `score(text) -> float` (VADER compound).
- `ingestion/news.py`, `ingestion/transcripts.py`: fixtures mock + ingestión.
- `storage/seed_news.py` (o extender seed): sembrar noticias/transcripts.
- `services/news_service.py`: feed con filtro por ticker, score agregado.
- `api/news.py`: `/api/news`, `/api/news/sentiment`, `/api/transcripts`.
- `pages/NewsPage.tsx` + componentes (NewsCard, SentimentTag, etc.).
- Tests: sentiment scorer, news ingestion (idempotencia), service.

## Criterio de aceptación
- Feed de noticias con tag de sentimiento coloreado, filtrable por activo.
- Score de sentimiento agregado por ticker.
- Sección de transcripciones con su sentimiento.
- `pytest` y `vitest` verdes; screenshot contra el spec.
