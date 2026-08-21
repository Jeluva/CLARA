# BACKLOG — CLARA

Cola de trabajo restante, en orden. Este archivo ES el estado del proyecto:
no hace falta releer BRIEF.md/AUTORUN.md/RESUMEN.md para saber qué falta,
alcanza con esto. Una tarea = un ciclo de loop. No arrancar la siguiente
hasta commitear la anterior.

## v1.0 — cierre (completo)

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

## v2 — de tracker a mesa de decisión de inversión

Diagnóstico (2026-08-21): hoy CLARA es un tracker de lo que el usuario ya
tiene, no una herramienta para decidir qué comprar. Todo lo calculado es
precio (retorno, volatilidad, drawdown, Sharpe, SMA/RSI/MACD, sentimiento)
y todo exige que el activo ya esté cargado como posición. Lo que enganchó
al usuario de la v1 fue el resumen de transcripciones de YouTube — la idea
de fondo es un panel tipo finviz: todos los datos que hacen falta para
juzgar si un activo (acción **o bono**) está bien valuado, en un solo lugar.

- [x] 1. **Fundamentals reales.** Hecho: tabla silver `fundamentals` (una
      fila por activo, snapshot que se sobreescribe en cada corrida, no una
      serie histórica), ingesta real vía `yfinance` `Ticker.info` con mock
      determinístico de fallback, quality check dedicado (`market_cap` >= 0
      cuando está presente; el resto de los campos son opcionales — un bono
      legítimamente no tiene P/E), endpoint
      `GET /api/research/fundamentals/{ticker}` y panel "Fundamentals" en
      Research (P/E, P/E fwd, P/B, EV/EBITDA, PEG, dividend yield, payout
      ratio, crecimiento ingresos/ganancias, márgenes, ROE, deuda/equity,
      target de analistas, recomendación, próximo earnings). Botón
      "Ingestar fundamentals" en Ingreso de datos. Verificado en vivo contra
      yfinance real: AAPL/KO con datos completos, SPY (ETF) parcial, AL30
      (bono) todo `None` — **pendiente real**: `yfinance.info` no trae nada
      útil para bonos (yield to maturity, duración, cupón, rating); si se
      quiere cubrir bonos hace falta otra fuente de datos, esto quedó fuera
      de esta vuelta.
- [ ] 2. **Modo "solo mirar" / watchlist.** Buscar y ver datos de un ticker
      sin tener que darlo de alta como posición primero (hoy Ingreso de
      datos exige activo + posición antes de ver nada).
- [ ] 3. **Screener tipo finviz.** Filtrar un universo de tickers por
      fundamentals + técnicos (P/E bajo, momentum positivo, sector, etc.)
      para generar ideas de candidatos, no solo analizar lo que ya se eligió
      de antemano.
- [ ] 4. **Comparador con valuación.** Sumar fundamentals/valuación al
      comparador de Research (hoy solo compara retorno/vol/drawdown/Sharpe
      entre tickers, sin decir si alguno está caro o barato).
- [ ] 5. **Simulación "qué pasa si compro esto".** Impacto en concentración/
      exposición/correlación de la cartera antes de comprar de verdad.
- [ ] 6. **Diario de tesis.** Por qué se compra, precio objetivo, stop-loss,
      convicción, y contraste posterior con el resultado real.
- [ ] 7. **Guía de tamaño de posición** según volatilidad del activo y
      presupuesto de riesgo de la cartera.
- [ ] 8. **Alertas** (precio, sentimiento, valuación) en vez de depender de
      entrar a mirar manualmente.
- [ ] 9. **Indicador de frescura de datos** en la UI: cuándo se actualizó
      por última vez cada fuente (relevante por los workarounds de
      yfinance/proxy ya documentados en fase-12).

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
