# ADR 0002 — Cuarentena de data quality en vez de descarte silencioso

## Contexto
Las fuentes financieras traen ruido: precios en cero, fechas futuras, tickers
desconocidos, sentimientos fuera de rango. Hay que decidir qué hacer con un
registro que no pasa validación al promover de bronze a silver.

## Decisión
Los registros que fallan un check **no se descartan**: se escriben en una tabla
`quarantine` con el payload crudo y el motivo de la falla (`failed_check`). Los
checks son funciones puras declarativas registradas por tabla; el motor de
promoción corre los checks y bifurca a silver (upsert idempotente) o a
cuarentena.

## Consecuencias
- (+) Trazabilidad total: puedo inspeccionar por qué se rechazó cada dato y
  reprocesarlo tras corregir la regla o la fuente.
- (+) Un lote con un registro malo no se cae entero; se procesa el resto.
- (+) Demuestra criterio de data engineering (observabilidad del pipeline), que
  es justamente lo que se quiere mostrar en el portfolio.
- (−) Tabla extra y lógica de bifurcación; costo bajo frente al beneficio.
- Alternativa descartada: dejar que Pydantic corte al deserializar — valida la
  forma, no la semántica financiera, y no captura el registro para auditarlo.
