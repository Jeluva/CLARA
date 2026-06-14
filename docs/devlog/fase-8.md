# Fase 8 — Pulido + publicación: dejar la historia contada

## El problema que resolvía

El código andaba y estaba testeado, pero "andar" no alcanza para una pieza de
portfolio. Faltaba lo que un reclutador ve primero: que **corra con un comando**,
que la arquitectura esté lista para producción, y que el README cuente una
historia en vez de listar comandos.

## Las decisiones de cierre

**Scheduler real, apagado por defecto.** El BRIEF pide APScheduler para los jobs
de ingestión. Lo armé con los tres jobs (precios al cierre, noticias cada 4
horas, transcripciones diarias) y su cron, arrancando desde el `lifespan` de
FastAPI. Pero **off por defecto** (`SCHEDULER_ENABLED=false`): no quiero que dev
ni los tests muten datos en segundo plano. Cada job abre su propia sesión, es
idempotente, y nunca tira una excepción que mate el scheduler. Un test verifica
que los tres jobs se registran con su trigger sin arrancar nada.

**Postgres-ready de verdad.** El `docker-compose.yml` levanta Postgres 16; pasar
de SQLite a Postgres es cambiar el `DATABASE_URL` y correr las mismas
migraciones de Alembic. El esquema es idéntico — esa fue la promesa desde la
Fase 1 y acá se cumple sin tocar una línea de modelo.

**README como narrativa.** Lo reescribí para que abra con el problema ("la info
de mis activos estaba dispersa"), muestre la solución (las 5 preguntas), explique
la arquitectura con el diagrama de capas, y sea **honesto sobre el alcance**: qué
es real y qué es mock, con el camino para enchufar lo real. Cierra con "qué
aprendí". Es lo primero que se lee y tiene que enganchar.

## La alternativa que descarté: dejar el scheduler corriendo en dev

Lo más vistoso hubiera sido que el scheduler arranque siempre y se vea "vivo".
Pero un proceso que muta la base mientras desarrollás o testeás es una fuente de
bugs no determinísticos. La decisión correcta es que esté listo y documentado,
pero que se prenda explícitamente. Sobriedad sobre brillo.

## Antes / después

- **Antes (Fase 0):** carpeta vacía.
- **Después:** app full-stack que corre con dos comandos, 5 pestañas pulidas,
  **73 tests backend + 7 frontend**, scheduler listo, Postgres-ready, y la
  historia contada en un README narrativo, 8 entradas de devlog, 5 ADRs y un
  RESUMEN de cierre.

## Criterios de aceptación cumplidos

- [x] Scheduler registrable y testeado (jobs con su trigger, off por defecto).
- [x] `docker-compose` con Postgres y el mismo esquema vía Alembic.
- [x] README narrativo (problema → solución → arquitectura → qué aprendí).
- [x] `RESUMEN.md` completo. Tests en verde. Corre con un comando.
