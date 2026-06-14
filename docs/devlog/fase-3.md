# Fase 3 — API: una capa de servicio que junta datos y matemática

## El problema que resolvía

Tenía dos mitades que no se hablaban: la capa de datos (silver, con posiciones y
precios) y el motor de analytics (funciones puras que no saben nada de la base).
Necesitaba pegarlas sin romper la separación de capas — sin que los routers
sepan de pandas, ni que analytics sepa de SQLAlchemy.

## La decisión de arquitectura: el service layer como único puente

Metí una **capa de servicio** en el medio. Es el único lugar del código que toca
la base *y* llama a analytics. Los routers quedan finos (orquestan y serializan
con Pydantic); analytics sigue puro. La regla es simple: si una función mezcla
`Session` con `numpy`, vive en `services/`.

`portfolio_service` carga las posiciones abiertas, las agrega por activo (con
costo promedio ponderado si hay varios lotes), trae el último precio y la serie
histórica, y de ahí arma todo: snapshots con P&L y pesos, métricas de riesgo,
exposición por sector/país/moneda, correlación, y la serie de valor vs. el
benchmark.

## La pieza que el advisor me marcó: el test que rompe fuerte

La parte más valiosa de esta fase no es un endpoint, es un **test de
integración**. Hasta acá, "métricas verificadas a mano" era cierto solo a nivel
unitario, con arrays de juguete. Nada corría la cadena real: seed → silver →
servicio → analytics.

El test más discriminante es engañosamente simple:

```python
# beta de una serie contra sí misma es exactamente 1
assert beta(spy_returns, spy_returns) == pytest.approx(1.0)
```

¿Por qué importa? Porque si la construcción de la `pd.Series` o la alineación de
fechas en el servicio estuvieran mal, beta(SPY, SPY) dejaría de dar 1 y el test
se caería a gritos. Es un canario barato para el bug más insidioso de esta capa:
desalinear series temporales. Alrededor agregué los guardas de rango: drawdown
≤ 0, volatilidad ≥ 0, pesos que suman 1, largo de la serie = días de historia.

## El número raro que NO es un bug: beta ≈ 0

Al pegar todo, la beta del portfolio contra SPY dio casi cero. Susto inicial —
hasta que recordé que los precios son **random walks independientes** (semilla
distinta por ticker, del seed de la Fase 1). Activos independientes no
correlacionan con un SPY también independiente, así que beta ~ 0 es exactamente
lo que tiene que pasar con datos mock. Con precios reales correlacionados, la
beta tomará valores con sentido. Lo dejo anotado para no asustarme de nuevo.

## La alternativa que descarté: routers gordos

Lo más rápido hubiera sido meter las queries y los cálculos directo en cada
endpoint. Pero eso entierra la lógica en la capa HTTP, la vuelve intesteable sin
levantar el server, y mezcla responsabilidades. La capa de servicio cuesta un
archivo más y devuelve testeo unitario directo sobre la lógica de negocio.

## Antes / después

- **Antes:** datos y matemática, cada uno por su lado.
- **Después:** `/api/portfolio`, `/metrics`, `/exposure`, `/history` y
  `/research/correlation` responden con datos reales del seed y aparecen
  documentados en `/docs` (Swagger). 53 tests en verde, incluyendo la cadena de
  integración completa.

## Criterios de aceptación cumplidos

- [x] Endpoints responden y están documentados en `/docs`.
- [x] Test de integración sobre el seed: `beta(SPY, SPY) ≈ 1`, drawdown ≤ 0,
      pesos suman 1, largo de serie = días de historia.
- [x] `pytest` verde (53 tests).
