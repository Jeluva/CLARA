# Fase 7 — Research & Macro: cerrar las cinco pestañas

## El problema que resolvía

Faltaban las dos pestañas más "analíticas": Research (¿mis activos están
realmente diversificados? ¿qué dice el técnico?) y Macro (¿cómo está el
contexto?). El apéndice del brief las marca como candidatas a V2, así que el
objetivo era hacerlas **buenas y honestas**, no sobre-pulidas: bien hechas donde
hay datos reales, claramente mockeadas donde no.

## La decisión: indicadores reales, macro mock declarado

**Research** corre sobre datos reales del seed. La matriz de correlación ya
existía desde la Fase 3; le sumé indicadores técnicos —SMA(20), SMA(50) y
RSI(14)— como funciones puras, testeadas a mano. El RSI tiene un caso de prueba
lindo: una serie que alterna +1/−1 da exactamente 50 (tantas subas como bajas),
y una serie monótona creciente da 100. Casos borde (sin pérdidas → 100, sin
ganancias → 0) resueltos explícitos, sin division-by-zero.

**Macro** es honestamente mock: índices, dólar MEP/CCL/blue, riesgo país y tasas
con valores realistas pero estáticos. AUTORUN prohíbe la red, así que en vez de
fingir un feed en vivo, la pestaña **dice que son mock** y el código documenta
exactamente qué fuente real va en cada lugar (yfinance, dolarapi, riesgo país).
La forma del dato (valor + variación) es la que consume la UI, así que enchufar
la fuente real es un drop-in sin tocar el front.

## Lo que la correlación cuenta (y por qué da casi cero)

El heatmap muestra la diagonal en 1.00 y casi todo lo demás cerca de 0. No es un
bug: los precios del seed son random walks independientes, así que no
correlacionan. Con precios reales el heatmap mostraría los clusters que importan
(las tres tech moviéndose juntas, el bono por su lado). La herramienta para
**detectar falsa diversificación** está lista; le falta el dato real, que entra
cuando se enchufa la fuente.

## La alternativa que descarté: inventar correlaciones "lindas"

Podría haber falseado los precios para que el heatmap mostrara clusters
vistosos. Pero eso es mentirle al que mira. Prefiero un heatmap honesto sobre
datos mock + un ADR que explica qué se vería con datos reales, que un gráfico
bonito que no significa nada.

## Antes / después

- **Antes:** Research y Macro eran placeholders.
- **Después:** las **cinco pestañas** están completas. Research: heatmap de
  correlación + gráfico de precio con medias móviles y panel de RSI con bandas
  70/30, con selector de activo. Macro: tarjetas tipo ticker agrupadas
  (índices / dólar / tasas) con su variación coloreada y el aviso de mock.

## Criterios de aceptación cumplidos

- [x] Matriz de correlación (heatmap).
- [x] Indicadores técnicos (SMA 20/50, RSI 14) por activo, testeados a mano.
- [x] Macro con índices, dólar, riesgo país y tasas (mock declarado).
- [x] `pytest` (72) y `vitest` (7) verdes; build OK.
