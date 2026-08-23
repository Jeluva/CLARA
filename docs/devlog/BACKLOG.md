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

      **Investigación de fuentes para renta fija argentina (2026-08-21,
      navegado en vivo con Chrome — sin API no importa, scraping con
      Playwright sirve igual que en el proyecto content-creator):**
      - `data912.com` — API JSON gratis, sin login, viva. `/live/arg_bonds`
        (soberanos + provinciales mezclados), `/live/arg_corp` (ONs),
        `/live/arg_cedears`, `/live/mep`, `/live/ccl`. Solo precio/bid/ask/
        volumen — **sin TIR ni duration**.
      - `bonistas.com` — el mejor para **soberanos**: TIR, TEM, TNA,
        duration modificada (MD), paridad, próximo cupón (dQ/dF/c$m), todo
        en tablas HTML server-rendered (no hace falta JS pesado). Sin
        login. No cubre ONs ni provinciales.
      - `rava.com/herramientas/analisis-de-bonos` — mismo nivel de detalle
        que bonistas para soberanos (precio, TIR, duration, paridad).
        Rava además tiene `/cotizaciones/acciones-argentinas` con vista
        tipo finviz (52 sem., sparkline 30 días) — candidato para el
        ítem 3 (screener). Pese a la descripción de la página de bonos
        ("soberanos y provinciales"), **no encontré tabla de provinciales
        ni de ONs** en el sitio.
      - `portfoliopersonal.com/Cotizaciones/Ons` (PPI) — **el mejor para
        ONs**: 1074 obligaciones negociables listadas con TIR, precio,
        volumen, sin login, HTML paginado (50/página), actualiza cada 15
        min. Verificado en vivo (ver AES, Aeropuertos Arg. 2000, Banco
        Comafi, Banco Macro, etc. con TIR reales).
      - `puentenet.com/cotizaciones/bonos` — el único sitio con pestañas
        explícitas separadas "Argentina - Soberanos / Provinciales /
        Corporativos / Lebacs" en un solo lugar. Fuente: Bolsa de Comercio
        de Buenos Aires, delay de 30 min. HTML paginado, sin login.
        **Pendiente confirmar**: si la pestaña "Provinciales" trae TIR/
        duration poblados o solo precio (quedó a mitad de verificar).
      - **Pendiente de esta investigación**: confirmar la pestaña
        Provinciales de Puente: buscar una fuente de rating crediticio
        para ONs (FIX SCR, Moody's Local, S&P Argentina, o el registro de
        CNV); decidir si conviene consolidar todo en Puente (un solo
        scraper, 3 categorías) o combinar bonistas (soberanos, mejor
        calidad de dato) + PPI (ONs) + alguna fuente de provinciales
        aparte.
- [x] 2. **Modo "solo mirar" / watchlist.** Hecho: el backend ya soportaba
      esto (`asset_service.get_asset_summary` no exige posición, la
      ingestión de precios/fundamentals corre sobre todos los assets), el
      gap era 100% de navegación — la única forma de llegar a
      `/activo/:ticker` era desde una fila de posición en Portfolio. Se
      agregó un buscador de ticker en el TopNav (navega directo a
      `/activo/TICKER`); si el activo no existe todavía, `AssetDetailPage`
      muestra una tarjeta "agregar a seguimiento" en vez de un error 404 —
      un click crea el `Asset` (sin posición) y dispara ingestión de
      precios/fundamentals en background. De paso, Research ya no limitaba
      los selectores de "Indicadores técnicos" y "Comparador de activos" a
      los tickers con posición (`correlation.tickers`): ahora listan todos
      los assets, así los que solo están en watchlist también se pueden
      analizar ahí. La matriz de correlación en sí queda igual (tiene
      sentido que sea solo de lo que se tiene, mide diversificación real).
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
