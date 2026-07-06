# Fase 12 — Fixes de producción: routing, borrado, noticias y transcripciones

## El problema que resolvía

Ya en producción (Vercel + Render) aparecieron varios problemas reales que no
se veían en dev: 404 al navegar el SPA, ruido en la ingesta real de noticias
y transcripciones, y falta de trazabilidad de errores en ingestión.

## Lo que se hizo

**404 de Vercel al navegar/refrescar.** Faltaba `frontend/vercel.json` con
el rewrite SPA (`/* → /index.html`). Sin él, Vercel solo sabe servir
`index.html` en `/` — cualquier otra ruta pedida directo al servidor
(refresh, deep link) devolvía el 404 nativo de la plataforma en vez de
dejar que React Router la resuelva client-side.

**Noticias: link al artículo real + filtro de relevancia.** El título de
cada noticia ahora es un link (`target="_blank"`) a la URL real, tanto en
`NewsPage` como en la pestaña Noticias de `AssetDetailPage`. Además, la
ingesta real (NewsAPI) buscaba el ticker como texto libre en todo el
artículo — tickers cortos/ambiguos (`KO`, `AL30`, `GGAL`) traían resultados
sin relación real. Se cambió a `qInTitle` y se agregó `_is_relevant()`:
acepta si el nombre de la empresa aparece, o si el ticker aparece junto con
alguna palabra de contexto financiero (`shares`, `earnings`, `stock`, etc.),
para descartar coincidencias casuales (p. ej. "KO'd" en una nota de boxeo).

**Ingestión: dejar de tragar errores en silencio.** `list_latest_videos` y
`fetch_transcript` (en `app/ingestion/youtube.py`) capturaban cualquier
excepción de yt-dlp / youtube-transcript-api y devolvían `[]`/`None` en
silencio — la ingesta reportaba "0 promovidas" sin ninguna pista de qué
había fallado. Ahora se distingue: los casos legítimos de "no hay nada"
(captions deshabilitados, video no encontrado) siguen devolviendo `None`;
el resto se propaga como `ChannelFetchError`, se acumula en
`PromotionResult.errors` (con `_dedupe_errors` para colapsar duplicados) y
se expone en el `message` de `POST /api/ingestion/run`.

Esto permitió diagnosticar en vivo la causa real de "las transcripciones no
andan": YouTube bloquea las IPs de datacenter de Render con un error
explícito ("YouTube is blocking requests from your IP... most IPs from
cloud providers are blocked").

**Dos caminos para transcripciones reales sin ese bloqueo:**

1. **Proxy residencial (Webshare, pago).** `WEBSHARE_PROXY_USERNAME` /
   `WEBSHARE_PROXY_PASSWORD` (vacíos por default) rutean tanto yt-dlp como
   youtube-transcript-api por un proxy residencial cuando están
   configurados. Se probó con las IPs gratis de Webshare (datacenter) y
   fallan igual que Render — solo el plan "Residential" (pago) sirve.

2. **Script local (gratis).** `POST /api/transcripts/ingest-external`
   (protegido con el header `X-Ingest-Secret`, comparado contra
   `INGEST_SECRET`) acepta transcripciones ya scrapeadas y las inserta por
   el mismo camino de dedupe/promoción que la ingesta real.
   `backend/scripts/fetch_transcripts_local.py` hace el scraping real desde
   la máquina donde se lo corra (IP residencial del usuario, no bloqueada)
   y sube el resultado a ese endpoint. Probado en vivo: 10 transcripts
   reales bajados sin bloqueo en la primera corrida. YouTube rate-limitea
   por volumen de requests repetidos en poco tiempo (no es un bloqueo
   permanente) — correrlo como mucho una vez por día evita re-disparar el
   límite.

## Decisiones

- No se agregó autenticación general a la API (sigue sin haber login en
  todo el proyecto) — pero el nuevo endpoint de ingesta externa sí exige un
  secreto compartido porque escribe datos y está expuesto en internet sin
  ningún otro control.
- Se prefirió el script local sobre pagar un proxy residencial porque el
  usuario priorizó costo cero; el soporte de proxy queda implementado y
  listo por si en el futuro se decide pagarlo.
- El filtro de relevancia de noticias es heurístico (regex de palabra
  completa + lista de términos financieros), no un clasificador — suficiente
  para cortar los falsos positivos observados sin agregar dependencias.
