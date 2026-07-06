# BACKLOG — cierre de CLARA

Cola de trabajo restante, en orden. Este archivo ES el estado del proyecto:
no hace falta releer BRIEF.md/AUTORUN.md/RESUMEN.md para saber qué falta,
alcanza con esto. Una tarea = un ciclo de loop. No arrancar la siguiente
hasta commitear la anterior.

- [ ] 1. **Capturas finales.** Levantar backend (`uvicorn app.main:app`) y
      frontend (`npm run dev`), abrir cada pestaña con datos del seed y
      guardar un PNG por pestaña en `docs/screenshots/`: `portfolio.png`,
      `noticias.png`, `research.png`, `macro.png`, `ingreso.png`. Linkear
      las 5 desde el README (sección "Capturas"). Criterio de aceptación:
      los 5 PNG existen y el README los embebe con `![...]`.

- [x] 2. **YouTube transcripts reales.** Hecho en fase-12: no era un bug de
      la lib, es YouTube bloqueando IPs de datacenter (confirmado en vivo
      contra Render). Ingesta real vía yt-dlp + youtube-transcript-api
      queda implementada y funcionando; para sortear el bloqueo en prod hay
      dos caminos ya construidos: `POST /api/transcripts/ingest-external`
      + `scripts/fetch_transcripts_local.py` (gratis, corrido desde una IP
      residencial) o proxy Webshare Residential (pago,
      `WEBSHARE_PROXY_USERNAME/PASSWORD`). Ver `docs/devlog/fase-12.md`.

- [ ] 3. **Barrido final de cierre.** Correr `pytest` (backend) y
      `npm test` + `tsc --noEmit` (frontend) una sola vez cada uno al final
      de la tarea (no repetir corridas completas por cambios chicos, correr
      solo el archivo de test afectado mientras se itera). Grep de
      `TODO|FIXME|console.log|print(` fuera de scripts de debug conocidos;
      limpiar lo que aparezca. Confirmar que CI (GitHub Actions) sigue
      verde. Commit final: "Cierre: CLARA v1.0". Criterio: suite en verde,
      sin TODOs sueltos, commit hecho.

## Reglas del ciclo (para no gastar tokens de más)

- Al empezar una tarea: leer SOLO los archivos que esa tarea menciona. No
  releer BRIEF.md/AUTORUN.md/README.md completos salvo que la tarea lo pida.
- Nada de exploración abierta del repo (`Explore`, `Agent`, greps amplios)
  para tareas de esta lista — ya están acotadas a archivos/carpetas puntuales.
- Un test o build por tarea al final, no uno por cada cambio chico.
- Al terminar una tarea: tildarla acá (`[x]`), un commit, y seguir con la
  siguiente automáticamente. Sin devlog narrativo por tarea (eso ya se hizo
  en las fases 0-11) — alcanza con el mensaje de commit.
- Si una tarea queda bloqueada de verdad (no la de YouTube, que ya tiene su
  propia salida): escribir `docs/BLOCKED.md` con el detalle y seguir con la
  tarea siguiente de la lista, no detener todo el loop.
- Cuando las 3 tareas estén tildadas: actualizar `docs/devlog/RESUMEN.md`
  (sección "Pendiente opcional" → borrar lo resuelto) y quedar en idle. No
  inventar tareas nuevas.
