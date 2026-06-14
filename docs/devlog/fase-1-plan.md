# Fase 1 — Plan: Capa de datos (medallion + data quality)

## Objetivo
Modelar el esquema completo del BRIEF con SQLAlchemy, organizarlo en capas
medallion (bronze/silver/gold), implementar los checks de data quality con
cuarentena, y sembrar la DB con un portfolio de ejemplo realista (foco
argentino) más una serie histórica de precios para que la Fase 2 (analytics)
tenga con qué calcular.

## Archivos que voy a tocar
- `backend/app/storage/database.py` — engine, session, Base, `get_db`.
- `backend/app/storage/models/` — modelos por capa:
  - `silver.py`: Asset, Position, Transaction, Price, News, Transcript.
  - `gold.py`: MetricsDaily.
  - `bronze.py`: BronzeRecord (store genérico de payloads crudos).
  - `quality.py`: Quarantine.
- `backend/app/quality/checks.py` — checks declarativos por tabla.
- `backend/app/quality/promote.py` — motor bronze→silver con cuarentena e
  idempotencia.
- `backend/app/storage/seed.py` — portfolio de ejemplo + precios históricos
  (determinístico, documentado como mock).
- Alembic: `alembic.ini`, `migrations/`, migración inicial.
- `backend/tests/test_data_quality.py`, `test_promotion.py`, `test_seed.py`.

## Decisiones
- **Bronze genérico**: una sola tabla `bronze_records(source_table, payload,
  fetched_at, status)` en vez de una por fuente. Reprocesable y uniforme.
- **Idempotencia**: claves naturales con UNIQUE (ticker; asset_id+date en
  prices; video_id en transcripts; url en news) → upsert, no duplica.
- **Checks declarativos**: cada check es una función `(record) -> None | str`
  que devuelve el motivo de falla. Falla → cuarentena, nunca descarte silencioso.
- **Seed determinístico**: precios como random walk con semilla fija (sin red),
  documentado como mock; la conexión real va en fases posteriores.

## Criterio de aceptación
- `alembic upgrade head` crea todo el esquema en SQLite.
- Tests de data quality pasan: precio>0, fecha no futura, ticker existe,
  sentimiento ∈ [-1,1]; los que fallan terminan en `quarantine`.
- Test de idempotencia: correr el seed/promoción dos veces no duplica filas.
- La DB queda con assets, positions, transactions y ~1 año de prices de ejemplo.
