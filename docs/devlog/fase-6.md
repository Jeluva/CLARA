# Fase 6 — Noticias & Sentimiento: el sentimiento se calcula, no se inventa

## El problema que resolvía

La pestaña de noticias era la oportunidad de mostrar la otra mitad del proyecto:
NLP sobre datos no estructurados. Pero había una trampa fácil: hardcodear
"sentimiento: positivo" en cada noticia y que se vea lindo. Eso no demuestra
nada. Quería que el score fuera **computado de verdad**.

## La decisión de arquitectura: VADER en inglés, LLM en español como V2

Las noticias y transcripciones mock están en inglés —algo plausible para
CEDEARs, tickers de EE.UU. y canales de research— y las puntúo con **VADER**, un
analizador de sentimiento lexicón + reglas cuyo score `compound` ya viene
normalizado a [-1, 1]: justo nuestra convención. El sentimiento sale de correr
el texto por el analizador, no de una constante.

¿Y el español? VADER rinde flojo ahí. En vez de construir un VADER-en-español a
medias que después tiraría, lo dejé documentado en un ADR: el camino real para
español financiero es un LLM con un prompt simple. Decisión explícita y honesta
en lugar de una implementación tibia.

## El detalle honesto que VADER me regaló

Al ver los scores apareció algo revelador: el titular *"Nvidia smashes revenue
records on insatiable AI chip demand"* puntuó **negativo**. ¿Por qué? Porque
VADER es ingenuo al contexto financiero: "smashes" e "insatiable" no están en su
lexicón como cosas buenas para una acción. Lejos de esconderlo, es el mejor
argumento a favor del ADR: un lexicón genérico no entiende la jerga del mercado,
y por eso el LLM es el camino productivo. Un score que "casi siempre acierta" y
falla de forma interpretable es más honesto que uno hardcodeado que nunca falla
porque nunca piensa.

## La pieza de ingeniería: misma medallion, otra fuente

Las fuentes de noticias y transcripciones reusan **exactamente el mismo patrón**
que los precios: fetch (mock) → bronze → validar → promover a silver. El check
de sentimiento ∈ [-1, 1] de la Fase 1 ya estaba esperándolas. Idempotencia por
URL (noticias) y por video_id (transcripciones). Enchufar la fuente real —News
API, `youtube-transcript-api`— es cambiar solo el paso de fetch.

## La alternativa que descarté: guardar el sentimiento como string

Podría haber guardado "positivo"/"negativo" como etiqueta. Pero guardar el
**número** en [-1, 1] permite agregarlo (promedio por ticker), ordenarlo y
graficar tendencia. La etiqueta de color se deriva del número en el momento de
mostrar, no al revés.

## Antes / después

- **Antes:** la pestaña de noticias era un placeholder.
- **Después:** feed de 15 noticias con tag de sentimiento coloreado, filtrable
  por activo; score agregado por ticker (GGAL +0.77 … NVDA −0.41); panel de 4
  transcripciones resumidas con su sentimiento. Todo con scores VADER reales.
  Verificado en el navegador, incluido el filtro por ticker.

## Criterios de aceptación cumplidos

- [x] Feed de noticias con sentimiento coloreado, filtrable por activo.
- [x] Score de sentimiento agregado por ticker.
- [x] Sección de transcripciones con sentimiento.
- [x] `pytest` (67) y `vitest` (7) verdes; build OK.
