# Fase 1 — Capa de datos: el dato sucio no se tira, se pone en cuarentena

## El problema que resolvía

Una mesa de análisis vale lo que valen sus datos. Si un precio entra en cero, o
una noticia trae un sentimiento de 1.7, o llega un ticker que no tengo en mi
tabla de activos, no quiero que eso contamine en silencio mis métricas de
riesgo. Necesitaba una capa de datos que sea *confiable por diseño*: que valide
antes de dejar entrar, y que cuando algo falla lo guarde para inspección en vez
de descartarlo.

## La decisión de arquitectura: medallion con un bronze genérico

Implementé el modelo **medallion** del BRIEF, pero con una vuelta de tuerca en
bronze. En vez de una tabla cruda por fuente (un `raw_prices`, un `raw_news`…),
usé **una sola tabla `bronze_records`** con `source_table`, `payload` (JSON
crudo), `dedupe_key` y `status`. Cualquier fuente escribe ahí con la misma
forma, y el motor de promoción es uno solo para todas. Menos tablas, menos
código duplicado, y el `status` (`pending → promoted | quarantined`) hace de
máquina de estados del flujo medallion.

- **Bronze:** el JSON tal cual, reprocesable sin volver a llamar a la fuente.
- **Silver:** las entidades de negocio limpias y tipadas (`assets`,
  `positions`, `prices`, `news`, `transcripts`), cada una con su clave natural
  `UNIQUE` para que la ingestión sea idempotente.
- **Gold:** `metrics_daily`, que se llena en la Fase 2.

## La pieza de la que estoy más orgulloso: checks declarativos

Los checks de data quality son **funciones puras** `(payload, context) -> str |
None`: devuelven el motivo de la falla o `None` si el registro está sano. Un
registro `CHECKS` mapea cada tabla a su lista ordenada de checks:

```python
CHECKS = {
    "prices": [check_required("ticker", "date", "close"),
               check_close_positive,
               check_date_not_future("date"),
               check_ticker_exists],
    ...
}
```

¿Por qué así? Porque la validación queda *declarativa y testeable por separado*,
no enterrada dentro del código de ingestión. Agregar una regla es agregar una
función a una lista. Y cada función se testea sola, sin tocar la base.

El motor de promoción recorre los bronze pendientes, corre los checks, y bifurca:
si pasan, hace upsert en silver (idempotente sobre la clave natural); si fallan,
escribe el registro completo en `quarantine` con el motivo. **Nada se pierde en
silencio** — que era el objetivo.

## La alternativa que descarté: validar con Pydantic en el borde

Podría haber dejado que Pydantic rechace los payloads inválidos al deserializar.
Pero Pydantic tira una excepción y corta; yo quería *capturar* el registro malo,
guardarlo con su motivo, y seguir procesando el resto del lote. La cuarentena es
una decisión de producto (auditar datos sucios), no solo de parsing. Pydantic
valida la forma de la API; los checks validan la *semántica financiera*.

## El atajo honesto: precios mock determinísticos

AUTORUN prohíbe llamadas reales a la red en este run. Los precios son un
**movimiento browniano geométrico con semilla fija por ticker** — determinístico,
así el dataset es reproducible y los tests pueden afirmar valores exactos. Está
documentado como mock en el código; la ingestión real de precios entra en una
fase posterior, enchufando la fuente sin tocar el resto del pipeline.

## Antes / después

- **Antes:** esquema en la cabeza, nada en la base.
- **Después:** `alembic upgrade head` crea las 9 tablas; el seed deja 8 activos
  (book diversificado con foco argentino: CEDEARs de tech US, equities locales,
  un bono soberano, y SPY como benchmark), 7 posiciones con su transacción de
  apertura, y **2016 precios** (8 × 252 días hábiles) — 0 en cuarentena. Correrlo
  dos veces no duplica una sola fila.

## Criterios de aceptación cumplidos

- [x] `alembic upgrade head` crea el esquema completo en SQLite.
- [x] Checks de data quality testeados: precio > 0, fecha no futura, ticker
      existe, sentimiento ∈ [-1, 1]; los que fallan terminan en `quarantine`.
- [x] Promoción e ingestión idempotentes (test que corre dos veces sin duplicar).
- [x] DB sembrada con un portfolio de ejemplo y ~1 año de precios.
- [x] 18 tests en verde.
