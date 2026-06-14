# Fase 5 — Plan: Ingreso de datos (CRUD end-to-end)

## Objetivo
Formularios funcionando de punta a punta: cargar un activo y una posición desde
la UI y verlos aparecer en Portfolio. Más un botón de "forzar ingestión" por
fuente con feedback de éxito/error (mock).

## Archivos
- Backend:
  - `app/api/schemas.py`: schemas de request (AssetCreate, PositionCreate,
    TransactionCreate).
  - `app/services/crud_service.py`: alta/baja/listado validando reglas
    (ticker único, asset existe).
  - `app/api/data_entry.py`: routers `/api/assets`, `/api/positions`,
    `/api/transactions`, `/api/ingestion/run`.
  - tests `test_crud_service.py`.
- Frontend:
  - `lib/api.ts`: tipos + POST/DELETE helpers.
  - `components/Forms` y la página `DataEntryPage` con formularios + listas +
    feedback.

## Decisiones
- Validación en el service (ticker único, asset_id existe, cantidades > 0);
  errores → HTTP 400/404 con detalle, no 500.
- Borrado de activo en cascada (posiciones/precios) ya cubierto por el modelo.
- Ingestión real sigue mockeada (AUTORUN); el botón ejecuta el job mock y
  reporta cuántos registros promovió/cuarentenó.

## Criterio de aceptación
- Crear un activo + posición desde la UI y verlos en Portfolio.
- Validaciones devuelven errores legibles (ticker duplicado, asset inexistente).
- `pytest` y `vitest` verdes.
- Screenshot de la pestaña contra el spec.
