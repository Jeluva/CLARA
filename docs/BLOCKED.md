# BLOCKED — v4 ítem 1: bonos soberanos reales vía bonistas.com

**Estado (2026-08-23):** bloqueado, no descartado. Ver `docs/devlog/BACKLOG.md`
v4 ítem 1.

## Qué se intentó

`curl` a `https://bonistas.com` (HTML crudo, sin ejecutar JS) para confirmar
la estructura de la tabla de soberanos antes de escribir el parser. El sitio
es una SPA Next.js: el HTML estático solo trae un `__NEXT_DATA__` con
metadata SEO (título, descripción, OpenGraph) — nada de la tabla de bonos.
Los datos reales (TIR, TEM, TNA, duration, paridad) se cargan client-side
después de montar el JS, vía una llamada a alguna API propia que no quedó
identificada. Probar rutas alternativas a mano (`/soberanos`,
`/bonos-soberanos`, `/bonos/soberanos`, `/bonos`) dio 404 en las cuatro.

## Por qué está bloqueado

Sin ejecutar el JS de la página no hay forma de ver qué endpoint llama ni
qué forma tiene la respuesta. La sesión de Chrome (`claude-in-chrome`) no
está conectada ("Browser extension is not connected") — necesita el usuario
con la extensión instalada y logueado. `WebFetch` (que sí ejecuta/renderiza
la página antes de convertir a markdown) tampoco recuperó las columnas de
la tabla, probablemente porque son cargadas de forma asíncrona después del
render inicial que WebFetch captura.

## Qué hace falta para desbloquear

1. Con Chrome conectado: abrir bonistas.com, ir a la pestaña "Bonos en
   dólares" / sección de soberanos, y mirar la pestaña Network del
   navegador (o `mcp__claude-in-chrome__read_network_requests`) para
   encontrar el endpoint real que trae TIR/duration/paridad.
2. Confirmar el shape exacto de esa respuesta (JSON esperado: campos, tipos,
   si separa soberanos de otras categorías) antes de decidir el esquema de
   la tabla silver (nueva vs. extender `fundamentals`).
3. Si bonistas.com resulta no tener una API navegable directamente (ej. todo
   detrás de auth o con protecciones anti-bot), evaluar las alternativas ya
   investigadas en v2 ítem 1: `rava.com/herramientas/analisis-de-bonos`
   (mismo nivel de detalle) o construir sobre `data912.com` (API JSON
   gratis, viva, pero sin TIR/duration — solo precio/bid/ask).

## Qué NO está bloqueado

El resto de v4 (ítems 2 y 3) no depende de esto y se hace mientras tanto.
