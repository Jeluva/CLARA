# ADR 0001 — FastAPI + arquitectura medallion para datos financieros

## Contexto
CLARA tiene que demostrar a la vez ingeniería de datos y análisis de datos. Las
fuentes (precios, noticias, transcripciones, macro) son heterogéneas, algunas
poco confiables, y necesito poder reprocesar sin volver a llamar a la fuente.

## Decisión
- **Backend en FastAPI** (no Flask): tipado con Pydantic, documentación OpenAPI
  automática en `/docs`, y soporte async nativo para llamadas a fuentes externas
  con timeouts/retries.
- **Modelado medallion (bronze → silver → gold)**:
  - *Bronze*: dato crudo tal como llega (JSON, transcript completo). Permite
    reprocesar sin re-llamar la fuente.
  - *Silver*: limpio, tipado, deduplicado, con timestamps de ingestión.
  - *Gold*: métricas agregadas listas para servir.

## Consecuencias
- (+) Reprocesamiento barato y auditable; si cambia la lógica de limpieza,
  recomputo silver/gold desde bronze sin tocar la red.
- (+) Separación de responsabilidades clara para tests por capa.
- (−) Más tablas y más escritura que un modelo plano; se justifica por la
  trazabilidad, que es justamente lo que se quiere mostrar.
