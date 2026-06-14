# Fase 5 — Ingreso de datos: cerrar el círculo, cargar y ver aparecer

## El problema que resolvía

Hasta acá la cartera venía del seed. Para que CLARA sea una herramienta y no una
demo de solo lectura, tenía que poder cargar un activo y una posición desde la
UI y verlos aparecer en Portfolio. El círculo completo: formulario → API →
base → dashboard.

## La decisión de arquitectura: las reglas de negocio viven en el service

Las validaciones —ticker único, el activo tiene que existir, cantidades > 0— no
las puse en el router ni en el front. Viven en `crud_service`, que levanta
errores tipados (`ConflictError`, `NotFoundError`) que el router traduce a HTTP
409/404/400 con un mensaje legible. Nunca un 500 pelado. El front solo muestra
el `detail` que devuelve la API. Una sola fuente de verdad para "qué es válido".

El borrado de un activo arrastra sus posiciones y precios por el `cascade` del
modelo, no por lógica repetida en cada endpoint.

## La pieza que casi se ve como un bug (y por qué no lo es)

El botón "Forzar ingestión" corre una fuente de precios mock que trae el próximo
día hábil para cada activo. Mi primera versión hizo algo revelador: **mandó 8
registros a cuarentena**. ¿Error? No: el seed terminaba un viernes y el "próximo
día hábil" caía un lunes *en el futuro* respecto de hoy. El check
`check_date_not_future` —el de la Fase 1— hizo exactamente su trabajo y los
frenó.

Técnicamente correcto, pero un botón de "éxito" que reporta "8 en cuarentena" es
una mala experiencia. Así que ajusté dos cosas con criterio de producto:
1. La ingestión ahora **rellena el hueco hasta hoy** (nunca más allá): no
   fabrica precios que todavía no existen.
2. Moví la fecha de fin del seed un par de semanas hacia atrás, para que haya un
   hueco real que la ingestión "en vivo" tenga que recuperar.

Resultado: el primer click promueve los días faltantes (80 precios: 8 activos ×
10 días hábiles, 0 en cuarentena), y un segundo click no agrega nada
—idempotente—. La fuente sigue siendo mock determinístico, sin red, como manda
el protocolo.

## La alternativa que descarté: validar en el frontend

Podría haber chequeado el ticker duplicado en React antes de mandar. Pero eso
duplica la regla en dos lugares y deja la API insegura si alguien la llama
directo. La validación vive en el backend; el front se limita a mostrar el error
que vuelve. Menos código, una sola verdad.

## Antes / después

- **Antes:** la pestaña de ingreso era un placeholder; la cartera era inmutable.
- **Después:** dos formularios (activo / posición) con feedback de éxito/error,
  tablas con borrado, y el botón de ingestión. Cargué **TSLA** y una posición de
  10 @ $200 desde la UI y el Portfolio se actualizó solo: el costo invertido
  subió exactamente $2.000. Round trip completo, verificado en el navegador.

## Criterios de aceptación cumplidos

- [x] Crear un activo + posición desde la UI y verlos en Portfolio (verificado
      end-to-end en el navegador).
- [x] Validaciones con errores legibles (ticker duplicado → 409, activo
      inexistente → 404).
- [x] `pytest` (60) y `vitest` (7) verdes; build OK.
- [x] Ingestión idempotente que rellena hasta hoy sin cuarentena espuria.
