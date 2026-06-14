# Fase 2 — Plan: Analytics (métricas financieras testeadas)

## Objetivo
Implementar el motor de métricas de portfolio y riesgo como funciones puras,
testeadas con TDD y **verificadas a mano sobre un caso conocido**. Esta es la
pieza que un reclutador va a mirar con lupa: las cuentas tienen que estar bien y
demostrablemente bien.

## Módulos (todas funciones puras sobre arrays/series)
- `analytics/returns.py`: rendimiento total, rendimiento por activo, retornos
  diarios, rendimiento acumulado, time-weighted return.
- `analytics/risk.py`: volatilidad anualizada, max drawdown, Sharpe ratio,
  beta vs. benchmark.
- `analytics/exposure.py`: exposición por sector/país/moneda; concentración
  (peso top-3, índice Herfindahl-Hirschman).
- `analytics/correlation.py`: matriz de correlación entre activos.
- `analytics/portfolio.py`: orquestador que toma posiciones + precios y arma el
  snapshot (valor, P&L, pesos, serie del portfolio) que consumen las métricas.

## Decisiones
- Funciones puras que reciben datos (numpy/pandas), sin tocar la DB. La capa de
  servicio (Fase 3) las alimenta desde silver. Esto las hace triviales de testear.
- Convención de anualización: 252 días hábiles. Documentado.
- Sharpe con tasa libre de riesgo configurable (default 0), documentado en ADR.
- Manejo explícito de casos borde: series vacías, un solo punto, varianza cero.

## Criterio de aceptación
- `pytest` verde.
- Para cada métrica financiera, un test con números calculados a mano en el
  docstring/comentario (no "lo que devuelve la función", sino el valor esperado
  derivado por fuera).
- Casos borde cubiertos (serie vacía/constante → sin division-by-zero ni NaN
  silencioso).
