# Fase 8 — Plan: Pulido + publicación

## Objetivo
Dejar el proyecto listo para publicar: scheduler de ingestión documentado,
Postgres-ready con Docker, README final como narrativa, RESUMEN.md y "corre con
un comando".

## Archivos
- `backend/app/scheduler/jobs.py`: APScheduler que registra los jobs de
  ingestión (precios/noticias/transcripciones) con su cron; off por defecto.
- `backend/app/config.py`: flag `scheduler_enabled`.
- `backend/app/main.py`: arranque/parada del scheduler en el lifespan.
- `docker-compose.yml`: servicio Postgres para prod.
- `README.md`: reescritura narrativa (problema → solución → arquitectura → qué
  aprendí) con las 5 pestañas.
- `docs/devlog/RESUMEN.md`: cierre (qué quedó, qué es mock, decisiones, próximos
  pasos).
- `Makefile` o scripts: levantar todo con pocos comandos.

## Criterio de aceptación
- Scheduler registrable y testeado (los jobs se registran con su trigger).
- `docker-compose` define Postgres con el mismo esquema (cambia el connection
  string).
- README cuenta una historia, no es una lista de comandos.
- RESUMEN.md completo. Tests en verde. Commit final.
