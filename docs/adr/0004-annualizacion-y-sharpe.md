# ADR 0004 — Convenciones de anualización y Sharpe

## Contexto
Las métricas de riesgo necesitan convenciones fijas para ser comparables y
reproducibles: factor de anualización, tipo de desvío, definición de Sharpe.

## Decisión
- **Anualización: 252 días hábiles.** Constante única en
  `analytics.TRADING_DAYS_PER_YEAR`.
- **Desvío muestral (ddof=1).** Estimador insesgado; consistente entre
  volatilidad, Sharpe y beta.
- **Volatilidad** = `std(retornos_diarios, ddof=1) × √252`.
- **Sharpe anualizado** = `mean(exceso) / std(exceso, ddof=1) × √252`, con
  `exceso = retorno − tasa_libre/252`. Tasa libre de riesgo configurable,
  default 0 (documentado; para CEDEARs en USD se puede enchufar la T-bill).
- **Beta** = `cov(activo, benchmark) / var(benchmark)` con ddof=1 consistente.

## Consecuencias
- (+) Números reproducibles y comparables entre activos y en el tiempo.
- (+) Casos borde resueltos explícitamente: series cortas o de varianza cero
  devuelven 0.0 en vez de NaN/inf, así la capa de serving nunca propaga basura.
- (−) Sharpe con rf=0 sobreestima levemente frente a usar la tasa real; queda
  como parámetro para no clavar un supuesto.
