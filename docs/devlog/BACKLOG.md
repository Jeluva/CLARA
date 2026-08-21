# BACKLOG — cierre de CLARA

Cola de trabajo restante, en orden. Este archivo ES el estado del proyecto:
no hace falta releer BRIEF.md/AUTORUN.md/RESUMEN.md para saber qué falta,
alcanza con esto. Una tarea = un ciclo de loop. No arrancar la siguiente
hasta commitear la anterior.

- [x] 1. **Capturas finales.** Hecho: los 5 PNG existen en
      `docs/screenshots/` (portfolio, noticias, research, macro, ingreso) y
      el README los embebe en la sección "Capturas". De paso, tomar las
      capturas contra el seed real destapó un bug: `/research/correlation`
      tiraba 500 porque `get_correlation` no alineaba por fecha los
      historiales de precio de cada ticker antes de calcular retornos (los
      arrays podían tener distinta longitud). Arreglado en
      `portfolio_service.get_correlation` (alinea con
      `pd.concat(...).dropna()` antes de `daily_returns`), con test de
      regresión en `test_portfolio_service.py`.

- [x] 2. **YouTube transcripts reales.** Hecho en fase-12: no era un bug de
      la lib, es YouTube bloqueando IPs de datacenter (confirmado en vivo
      contra Render). Ingesta real vía yt-dlp + youtube-transcript-api
      queda implementada y funcionando; para sortear el bloqueo en prod hay
      dos caminos ya construidos: `POST /api/transcripts/ingest-external`
      + `scripts/fetch_transcripts_local.py` (gratis, corrido desde una IP
      residencial) o proxy Webshare Residential (pago,
      `WEBSHARE_PROXY_USERNAME/PASSWORD`). Ver `docs/devlog/fase-12.md`.

- [x] 3. **Barrido final de cierre.** Hecho: 97 tests backend (pytest) +
      16 frontend (vitest) en verde, `tsc --noEmit` sin errores. Grep de
      `TODO|FIXME|console.log|print(` no encontró nada fuera de lo
      esperado (`print(` solo en `seed_cli.py`, salida legítima de CLI).
      CI (GitHub Actions) en verde en los últimos runs. Rama local estaba
      2 commits detrás de origin (borrado de `BRIEF.md`/`AUTORUN.md`);
      sincronizada con fast-forward antes de commitear.

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
