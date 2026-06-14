# Fase 4 — Pestaña Portfolio: la vista que responde "¿cómo estoy parado?"

## El problema que resolvía

Toda la cañería estaba lista —datos, métricas, API— pero un reclutador no lee
JSON en Swagger. Necesitaba la **mesa de análisis** de verdad: abrir la pestaña
y responder de un vistazo cómo está parada la cartera. Valor, P&L, riesgo,
exposición, evolución. Sin ruido.

## La decisión de arquitectura: componentes tontos + un hook que centraliza

Armé la vista como **componentes presentacionales puros** (`Metric`, `Donut`,
`PositionsTable`, `RiskPanel`, `LineChartCard`) que solo reciben datos y pintan.
El estado de red vive en un único hook, `useApi`, que maneja loading/error de
una sola forma. ¿Por qué? Para no repetir el patrón "spinner / error / data" en
cinco lugares y que cada componente se pueda testear con props fijas, sin red.

Los colores de los gráficos no se hardcodean: Recharts toma los tokens desde
`theme.ts`, el mismo origen que Tailwind. Un cambio de paleta es un cambio en un
archivo, y la línea del portfolio siempre es el azul iOS del acento.

## El loop de diseño: comparar contra el spec y corregir

Saqué un screenshot y lo comparé contra el spec del BRIEF. La mayoría cerraba
—dark, cards #1C1C1E, P&L verde/rojo, números tabulares— pero saltó **una
diferencia que importaba**: el donut "Por moneda" mostraba USD 100%.

Técnicamente correcto (así estaba el seed), pero conceptualmente vacío: la
exposición peso/dólar es *uno de los argumentos centrales* de una herramienta
con foco argentino. Un donut de un solo color no responde la pregunta que esa
tarjeta existe para responder. Así que corregí el seed —GGAL e YPFD, equities
locales, pasaron a ARS— y el donut pasó a contar la historia real: USD 93.8% /
ARS 6.2%. Es exactamente el tipo de detalle que el "loop del inversor exigente"
busca: ¿qué pregunta NO puede responder esta vista? Y arreglarlo.

## La alternativa que descarté: una librería de dashboard

Podría haber traído un kit de dashboard con grillas y widgets pre-hechos. Pero
el valor de este proyecto es el criterio de diseño propio, no ensamblar piezas
de otro. Componentes a medida sobre los tokens del theme dan control total sobre
la densidad y la jerarquía, que es justo lo que el spec pide cuidar.

## Antes / después

- **Antes:** la pestaña Portfolio era un placeholder "En construcción".
- **Después:** un dashboard completo con datos reales del backend — KPIs (valor
  $130k, P&L +9.45%), evolución acumulada vs. SPY, panel de riesgo (volatilidad,
  drawdown, Sharpe, beta, concentración), tres donuts de exposición
  (sector/país/moneda) y la tabla de posiciones ordenada por valor con P&L
  coloreado. `tsc`, `vitest` (7 tests) y el build, en verde.

## Criterios de aceptación cumplidos

- [x] La pestaña muestra datos reales del backend.
- [x] Se ve como el spec: dark, acento azul, P&L semántico, densidad alta y
      respirada, números tabulares.
- [x] `npm test` y `tsc` verdes.
- [x] Screenshot comparado contra el spec; corregida la diferencia de mayor
      impacto (exposición por moneda).
