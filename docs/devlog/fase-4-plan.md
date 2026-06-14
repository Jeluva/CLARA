# Fase 4 — Plan: Pestaña Portfolio (la vista principal)

## Objetivo
La vista principal completa y pulida, consumiendo la API de la Fase 3: KPIs de
valor y P&L, tabla de posiciones, gráfico de evolución vs. benchmark, donuts de
exposición y panel de métricas de riesgo. Tiene que verse como el spec del BRIEF.

## Archivos
- `frontend/src/lib/format.ts`: helpers de moneda, %, signo y color semántico.
- `frontend/src/lib/api.ts`: tipos + fetchers de los endpoints de portfolio.
- `frontend/src/components/`: `Metric.tsx` (KPI), `Stat.tsx`, `Donut.tsx`,
  `LineChartCard.tsx`, `PositionsTable.tsx`, `RiskPanel.tsx`, `Spinner.tsx`.
- `frontend/src/pages/PortfolioPage.tsx`: ensamblar todo con estados
  loading/error.
- `frontend/src/hooks/useApi.ts`: hook de fetch con loading/error.
- Tests vitest: format helpers + render de la página con fetch mockeado.

## Decisiones
- Recharts para línea (evolución) y donut (exposición), coloreado con los tokens
  del theme (`theme.ts`).
- Números con `tabular-nums`; verde/rojo semántico para P&L.
- Hook `useApi` para no repetir loading/error en cada componente.
- Formateo de moneda con `Intl.NumberFormat`.

## Criterio de aceptación
- La pestaña Portfolio muestra datos reales del backend.
- Se ve como el spec: dark, cards #1C1C1E, acento azul, P&L verde/rojo,
  densidad alta pero respirada.
- `npm test` y `tsc` verdes.
- Screenshot comparado contra el spec; corregir hasta 5 diferencias.
