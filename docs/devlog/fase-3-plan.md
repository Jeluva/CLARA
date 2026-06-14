# Fase 3 — Plan: API (service layer + routers FastAPI)

## Objetivo
Conectar la capa de analytics (Fase 2) con los datos de silver (Fase 1) a través
de una capa de servicio, y exponerla con routers FastAPI documentados en Swagger.

## Archivos
- `backend/app/services/portfolio_service.py`: lee posiciones/precios de silver,
  arma snapshots, serie de valor, métricas de riesgo vs benchmark (SPY),
  exposición y correlación.
- `backend/app/services/market_data.py`: helpers para cargar series de precios
  como `pd.Series` y el último precio por activo.
- `backend/app/api/schemas.py`: modelos Pydantic de respuesta.
- `backend/app/api/portfolio.py`: `/api/portfolio`, `/metrics`, `/exposure`,
  `/history`.
- `backend/app/api/research.py`: `/api/research/correlation`.
- `backend/app/api/news.py`, `macro.py`: stubs que devuelven lo disponible
  (se completan en Fases 6-7).
- `backend/app/main.py`: incluir routers + dependencia de DB.
- Tests: `test_portfolio_service.py` (integración sobre el seed),
  `test_api.py` (endpoints responden y tienen forma correcta).

## Decisiones
- La capa de servicio es la única que mezcla DB + analytics; los routers solo
  orquestan y serializan. Mantener la separación de capas del BRIEF.
- Alineación temporal de series con pandas; correlaciones con NaN → 0
  (decisión de serving, anotada).
- Benchmark = SPY (sin posición, solo serie de precios).

## Criterio de aceptación (incluye lo que pidió el advisor)
- Endpoints responden y aparecen en `/docs`.
- Test de integración sobre el seed real:
  - `beta(SPY, SPY) ≈ 1.0` (alineación de fechas correcta).
  - `max_drawdown ≤ 0`, `volatility ≥ 0`.
  - pesos de las posiciones suman 1.
  - largo de la serie de valor = días de historia de precios.
- `pytest` verde.
