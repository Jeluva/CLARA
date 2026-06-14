# ADR 0003 — `portfolio_value_series` usa shares constantes (backtest del basket)

## Contexto
La pestaña Portfolio muestra "rendimiento acumulado vs. benchmark". Para
calcular la serie de valor del portfolio en el tiempo hay que decidir qué
cantidad de cada activo aplicar en cada fecha histórica.

## Decisión
`portfolio_value_series` calcula `V(t) = Σ_i cantidad_actual_i × precio_i(t)`:
aplica las **tenencias de hoy** a toda la historia de precios. Es un backtest de
"qué hubiera hecho el basket que tengo ahora", no la serie de mi P&L realizado
(que depende del timing de entrada de cada posición: AAPL abrió hace 240 días,
YPFD hace 160).

## Consecuencias
- (+) Es la elección **correcta y convencional para las métricas de riesgo**
  (volatilidad, drawdown, Sharpe): describen el riesgo de *lo que tengo hoy*.
- (+) Simple, determinístico y testeable.
- (−) Para "rendimiento acumulado", es el retorno *hipotético* del basket, no el
  *realizado*. Son preguntas distintas.
- **Roadmap (V2):** una serie de P&L realizada que respete `opened_at` y las
  transacciones (time-weighted return sobre flujos reales) para separar
  "performance del basket" de "performance de mis decisiones de timing".

Documentar esto explícitamente: dejado implícito se lee como bug; explícito se
lee como criterio.
