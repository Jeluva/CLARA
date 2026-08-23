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
- [x] 3. **Screener tipo finviz.** Hecho: universo curado de 28 tickers
      líderes (`app/ingestion/universe.py` — CEDEARs de EE. UU. como
      "cedear", Merval como "equity", soberanos AR como "bond") con endpoint
      `POST /api/screener/seed` que crea los que falten (idempotente, no
      pisa los que ya existen) + `GET /api/research/screener`
      (`screener_service.get_screener`) que devuelve fundamentals +
      técnicos (retorno 1M, RSI14, tendencia SMA20/50) por activo. Página
      nueva "Screener" en el nav: tabla ordenable por columna, filtros de
      texto/sector/clase/P·E máximo/momentum positivo, botón "Cargar
      universo ampliado" que siembra + dispara ingestión de precios y
      fundamentals. Probado en vivo contra el backend real (no mock): 20
      activos nuevos creados, 4490 precios y 28 fundamentals ingestados sin
      errores. Confirma el gap ya documentado en el ítem 1: los 4 bonos
      soberanos (AL30/GD30/AL35/AE38) devuelven precio y fundamentals
      `null` en yfinance — el screener lo maneja bien (celda "—"), pero
      cubrir bonos de verdad sigue pendiente de otra fuente de datos.
- [x] 4. **Comparador con valuación.** Hecho: `research_service.compare_assets`
      ahora suma P/E, P/E fwd, P/B, EV/EBITDA, dividend yield y ROE (join
      contra `Fundamentals` por ticker, `None` si el activo no tiene
      fundamentals ingeridos todavía — igual que el resto del comparador).
      `AssetComparator` en `ResearchPage.tsx` separa la tabla en dos
      secciones ("Precio y riesgo" / "Valuación — ¿caro o barato?") en vez
      de mezclar todo en una lista plana de filas.
- [x] 5. **Simulación "qué pasa si compro esto".** Hecho: nuevo
      `portfolio_service.simulate_purchase(db, ticker, amount)` — recibe un
      monto en USD, arma una cartera hipotética (suma a la posición existente
      si ya se tiene el activo, o la crea desde cero si no) sin escribir nada
      en la DB, y devuelve antes/después de concentración top-3, Herfindahl,
      exposición por sector/país/moneda, y la correlación promedio del activo
      contra la cartera actual (ponderada por peso de cada tenencia). Nuevo
      endpoint `POST /api/portfolio/simulate` (404 si el ticker no existe o
      no tiene precio ingerido; 422 si el monto no es positivo, validado por
      Pydantic). Pestaña nueva "Simular compra" en `AssetDetailPage`: input
      de monto + botón, y card con peso resultante, delta de concentración/
      HHI, lectura de correlación (diversifica / correlación moderada / se
      mueve parecido) y el corrimiento de exposición en la categoría propia
      del activo (sector/país/moneda). Probado en vivo contra el backend real
      (no mock): compra nueva (SPY, no tenido) diluye top3 de 0.892 a 0.861 y
      HHI de 0.526 a 0.492; ampliar una posición existente (AAPL) sube su
      peso de concentración; ticker inexistente y monto ≤0 devuelven error
      claro. Verificación de UI en navegador bloqueada por el sandbox de la
      herramienta de automatización (no puede llegar a `localhost` — no es
      un problema del código); cubierto en cambio con `tsc --noEmit`, build
      de producción y la suite de vitest en verde, más las pruebas de
      `simulate_purchase` en `test_portfolio_service.py`.
- [x] 6. **Diario de tesis.** Hecho: tabla silver nueva `theses` (migración
      Alembic `thesis`) — un activo puede tener muchas entradas de tesis a lo
      largo del tiempo, cada una con motivo (texto libre), precio objetivo,
      stop-loss, convicción (baja/media/alta) y `price_at_entry` (capturado
      automáticamente del último precio al crearla, para poder contrastar
      después). `thesis_service.py` calcula en cada lectura el contraste
      contra el precio real actual: retorno desde la entrada y un status
      (`en_curso` / `objetivo_alcanzado` si el precio ya superó el target /
      `stop_tocado` si cayó al stop / `sin_precio` si el activo no tiene
      precio ingerido). CRUD completo: `GET /api/theses?ticker=` (filtro
      opcional), `POST /api/theses`, `DELETE /api/theses/{id}` — mismo patrón
      de errores tipados (404/400) que `crud_service.py`. Pestaña nueva
      "Diario de tesis" en `AssetDetailPage`: formulario (motivo, objetivo y
      stop opcionales, convicción) + historial con badge de estado y retorno
      desde la entrada coloreado. Se agregó `Textarea` a `components/Field.tsx`
      (no existía, solo `Input`/`Select`). Probado en vivo contra el backend
      real: creación con `price_at_entry` capturado del precio real de AAPL,
      status `objetivo_alcanzado` cuando el target queda por debajo del
      precio actual, `stop_tocado` cuando el stop queda por encima, y delete
      funcionando. 10 tests nuevos en `test_thesis_service.py`.
- [x] 7. **Guía de tamaño de posición.** Hecho:
      `portfolio_service.get_position_size_guide(db, ticker, risk_budget_pct)`
      — regla de tamaño escalado por volatilidad: monto sugerido = (valor de
      cartera × presupuesto de riesgo) ÷ volatilidad anualizada del activo, así
      un activo más volátil recibe menos peso para el mismo presupuesto de
      riesgo. `risk_budget_pct` son unidades de volatilidad anualizada (no la
      convención de distancia al stop de `theses.stop_loss`); default 3%,
      calibrado a mano contra el seed (AAPL ≈11%, NVDA ≈6%, KO ≈18% de peso
      sugerido — rango single-digit/low-teens esperado, no 1-2% aplastado).
      Tope duro `MAX_POSITION_WEIGHT=25%` para que un activo de vol casi nula
      (bono) no se sugiera concentrado. Normaliza a USD igual que
      `simulate_purchase` (divide por `fx_service.usd_ars_rate()` para
      activos ARS) — cubierto con test dedicado sobre GGAL, no solo un ticker
      USD. Nuevo endpoint `GET /api/portfolio/position-size/{ticker}?risk_budget_pct=`
      (`Query(gt=0, le=1)`), 404 si no hay precio para calcular volatilidad.
      Pestaña nueva "Tamaño de posición" en `AssetDetailPage`: input de
      presupuesto (%) + botón, card con volatilidad, tamaño sugerido (monto y
      % de cartera, con aviso si pegó en el tope), posición actual, y el
      delta ("podrías sumar" / "por encima de lo sugerido" si ya se pasó).
      Sin precio todavía (los bonos soberanos AR, ítem 1) muestra un mensaje
      claro en vez de un error. 5 tests nuevos en `test_portfolio_service.py`
      (escala inversa a volatilidad, normalización ARS, tope de
      concentración, ticker inexistente, presupuesto ≤0). Verificado en vivo
      contra el seed real (no mock): valores de peso sugerido en el rango
      esperado para AAPL/NVDA/KO/GGAL/AL30, tope funcionando. `tsc --noEmit`,
      build de producción y vitest en verde.
- [x] 8. **Alertas.** Hecho: tabla silver nueva `alerts` (migración Alembic
      `alerts`) — regla ticker + métrica (`price` / `sentiment` / `pe_ratio`)
      + condición (`above` / `below`) + umbral. Sin scheduler ni canal de
      notificación: `alert_service.list_alerts` evalúa cada regla en vivo
      contra el mismo dato que ya muestran Resumen/Noticias/Fundamentals
      (`latest_prices`, promedio de sentimiento de noticias, `pe_ratio` de
      `fundamentals`), así queda tan fresco como la última ingestión — mismo
      patrón que `thesis_service` computando status al leer. CRUD:
      `GET /api/alerts?ticker=&only_triggered=`, `POST /api/alerts`,
      `DELETE /api/alerts/{id}`. Pestaña nueva "Alertas" en
      `AssetDetailPage`: formulario (métrica/condición/umbral) + lista con
      badge de estado (disparada/en seguimiento/sin dato/inactiva) y valor
      actual. Como no hay push/email, la visibilidad "sin entrar a mirar" es
      un badge en el `TopNav` (visible en cualquier pestaña) con la cuenta de
      alertas disparadas y un dropdown que linkea directo al activo. 10 tests
      nuevos en `test_alert_service.py` (trigger/no-trigger por métrica,
      sentimiento/PE sin dato, filtros, validaciones, delete). Verificado en
      vivo contra un seed real (sqlite + `alembic upgrade head` +
      `seed_cli` + ingestión mock de fundamentals, no mock de test): alerta
      de precio y de P/E disparan correctamente contra AAPL real, alerta de
      sentimiento con umbral no alcanzado queda "en seguimiento",
      `only_triggered` filtra bien. `tsc --noEmit`, build de producción y
      vitest en verde.
- [x] 9. **Indicador de frescura de datos.** Hecho: `freshness_service.get_freshness`
      lee `bronze_records.fetched_at` (la única marca de tiempo que escribe
      *todo* ingestor, sin importar el esquema silver de cada fuente —
      `transcripts` ni siquiera tiene su propio `ingested_at`) y agrupa por
      `source_table` para dar, por cada una de las 4 fuentes
      (`prices`/`news`/`transcripts`/`fundamentals`), cuándo promovió datos
      por última vez (`last_success_at`) y cuándo se intentó por última vez
      en general (`last_attempt_at`) — si difieren, la corrida más reciente
      no promovió nada nuevo (relevante por los workarounds de yfinance/
      YouTube de fase-12). Endpoint nuevo `GET /api/ingestion/freshness`.
      En Ingreso de datos, debajo de los botones "Ingestar…", una lista con
      punto verde/gris/rojo (ok / nunca / corrió pero no promovió nada) y
      tiempo relativo ("hace 3 h"); se refresca sola después de cada
      ingestión forzada, sin recargar la página. 4 tests nuevos en
      `test_freshness_service.py`. Verificado en vivo contra un seed real
      (sqlite + `alembic upgrade head` + `seed_cli`, no mock de test):
      precios/noticias/transcripciones muestran su timestamp real de la
      corrida del seed, fundamentals (nunca ingerido en el seed) da `None`
      en ambos campos como se esperaba. `tsc --noEmit`, build de producción
      y vitest en verde; 147 tests backend en verde.

Con los ítems 7-9 tildados, la v2 queda completa.

## v3 — organización: múltiples portfolios

- [x] 1. **Selector de portfolio.** Hecho: tabla silver nueva `portfolios`
      (id, nombre único, `created_at`) — `Position` ahora tiene
      `portfolio_id` (FK, `NOT NULL`). Migración Alembic crea la tabla,
      inserta un portfolio "TestPortfolio" (agrupa lo que antes eran
      posiciones sin dueño) y hace el backfill antes de poner la columna
      `NOT NULL` (SQLite no permite agregar una columna `NOT NULL` a una
      tabla con filas en un solo paso). `portfolio_service` recibe
      `portfolio_id: int | None` en cada función que lee posiciones
      (`get_portfolio_overview`, `get_risk_metrics`, `get_exposure`,
      `get_history`, `get_realized_history`, `get_correlation`,
      `simulate_purchase`, `get_position_size_guide`) —
      `portfolio_id=None` mergea todas las posiciones de todos los
      portfolios, que es exactamente el pedido de "una opción que mergee
      los portfolios para ver todas las posiciones en total": no hay un
      camino de agregación separado, mergear es simplemente no filtrar.
      CRUD nuevo: `GET/POST /api/portfolios`,
      `PATCH /api/portfolios/{id}` (renombrar) — sin DELETE, no lo pidió
      el usuario y cascadear borraría posiciones en silencio. Frontend:
      `PortfolioProvider` (contexto + `localStorage`, sobrevive un
      refresh) expone el portfolio activo a toda la app; `PortfolioSwitcher`
      (flecha/chevron al lado del título "Portfolio") permite cambiar de
      portfolio, ver "Todos" (mergeado), renombrar inline y crear uno
      nuevo. `Ingreso de datos` ahora pide portfolio al crear una posición
      y muestra a qué portfolio pertenece cada una en la tabla. La página
      Portfolio, la card de posición en el resumen del detalle de activo
      (`asset_service.get_asset_summary`) y las pestañas "Simular
      compra"/"Tamaño de posición" quedan todas scopeadas al mismo
      portfolio activo -- se detectó en revisión que dejar la card de
      resumen mergeada mientras esas dos pestañas quedaban scopeadas
      hubiera mostrado dos números de "cuánto tengo" distintos en la
      misma pantalla. El chatbot (`chat_service`) sí queda mergeado a
      propósito: es contexto para un LLM, no un número mostrado.
      `research.get_correlation` queda sin cambios (mide diversificación
      real de lo que se tiene, mergeado, como ya documentaba el ítem 2 de
      v2) y `Transaction` queda sin `portfolio_id` (nada la lee todavía).
      La migración inserta el portfolio default resolviendo su id **por
      nombre** después del insert, no con un `id=1` hardcodeado -- en
      Postgres un insert con id explícito no avanza la secuencia
      `SERIAL`, así que el primer `POST /api/portfolios` en producción
      hubiera chocado contra esa misma id (se detectó en revisión, antes
      de deployar). 3 tests nuevos de aislamiento/merge/consistencia
      (`test_portfolio_service.py`, `test_asset_service.py`) + 6 de CRUD
      de portfolios en `test_crud_service.py` (151 tests backend en
      verde). Verificado en vivo contra el backend real (no mock, puerto
      alternativo para no pisar un proceso dev preexistente): overview
      mergeado = overview de TestPortfolio antes de crear un segundo
      portfolio; un segundo portfolio arranca vacío; una posición creada
      en él no aparece en el primero y sí en el mergeado; rename
      funciona; nombre duplicado devuelve 409; migración probada con
      downgrade + upgrade en la misma corrida. Verificación de UI en
      navegador bloqueada por el mismo límite de sandbox que el ítem 5
      de v2 (no puede llegar a `localhost`); cubierto en cambio con
      `tsc --noEmit`, build de producción y la suite de vitest en verde
      (23 tests). **Pendiente para quien levante el servidor dev**: el
      proceso de `uvicorn` que ya estaba corriendo en el puerto 8000 fue
      levantado con el código *antes* de esta migración -- su modelo
      `Position` en memoria no tiene `portfolio_id`, así que cualquier
      alta de posición a través de él va a fallar contra la DB ya
      migrada (violación NOT NULL). Reiniciarlo para que cargue el
      código nuevo.

## v4 — cerrar el gap de renta fija + consistencia multi-portfolio

Diagnóstico (2026-08-23): con v3 cerrada, CLARA cubre bien acciones/CEDEARs
(fundamentals, screener, comparador, simulación, tesis, tamaño de posición,
alertas) pero tiene tres huecos concretos que quedaron documentados o
expuestos por el trabajo reciente:

1. **Bonos soberanos AR sin dato real.** Flagged dos veces (v2 ítem 1, v2
   ítem 3): AL30/GD30/AL35/AE38 devuelven `null` en precio y fundamentals
   porque `yfinance` no cubre renta fija argentina. Ya hay investigación de
   fuentes hecha (bonistas.com — TIR/TEM/TNA/duration modificada/paridad,
   HTML server-rendered, sin login, el mejor para soberanos). Es el gap más
   repetido y el que más rompe la promesa de v2 ("acción **o bono**").
2. **`Transaction` sin `portfolio_id`.** La migración de v3 lo dejó afuera
   a propósito ("nada la lee todavía"), pero ahora que multi-portfolio es
   real, el historial de transacciones no se puede filtrar ni atribuir a
   un portfolio específico — inconsistente con posiciones, que sí lo tienen.
3. **No hay una vista de arranque.** Alertas, tesis en curso y frescura de
   datos viven cada una en su pestaña; para saber "¿qué necesita mi
   atención hoy?" hay que entrar a las tres. Encaja con el espíritu de v2
   (mesa de decisión, no solo tracker).

- [ ] 1. **Bonos soberanos reales vía bonistas.com.** Scraper (Playwright,
      mismo patrón que el resto de la ingestión) contra la tabla de
      soberanos de bonistas.com: TIR, TEM, TNA, duration modificada,
      paridad, próximo cupón. Tabla silver nueva (o extensión de
      `fundamentals` con columnas opcionales — decidir al implementar cuál
      ensucia menos el esquema) para los 4 bonos ya en el universo
      (AL30/GD30/AL35/AE38). Quality check dedicado (TIR/duration
      razonables, no negativos). Reemplazar el "—" del screener/
      fundamentals por el dato real para esos 4 tickers. Confirmar en vivo
      con Chrome la estructura HTML actual antes de escribir el parser (la
      investigación de v2 es de hace semanas, el sitio puede haber
      cambiado). ONs (PPI) y provinciales (Puente) quedan fuera de esta
      vuelta — solo soberanos, que es lo que ya está en el universo.
- [x] 2. **`portfolio_id` en `Transaction`.** Hecho: migración Alembic
      (mismo patrón que v3: columna nullable, backfill, `NOT NULL`
      después) — si todas las posiciones existentes de un activo
      pertenecen a un solo portfolio se atribuye ahí; si es ambiguo (o no
      hay posición) cae al portfolio más viejo. `crud_service.create_transaction`
      ahora exige `portfolio_id` y 404 si el portfolio no existe (mismo
      patrón que `create_position`). `TransactionCreate` lo pide en el
      body. `seed.py` tenía el mismo bug que motivó este ítem: creaba la
      posición con `portfolio_id` pero la transacción de apertura
      emparejada sin él — arreglado de paso (si no, el seed rompía con
      `IntegrityError` apenas se corría la migración). Frontend:
      `TransactionForm` en Ingreso de datos gana el mismo selector de
      portfolio que `PositionForm`, mismo default (portfolio activo, o el
      primero si está en "Todos"). No hay `GET /api/transactions` todavía
      (nada lo consume — ni la UI ni ningún service lee `Transaction`),
      así que no hay filtro por portfolio que enchufar del lado de
      lectura; el valor de este ítem es la consistencia del dato hacia
      adelante. 4 tests nuevos en `test_crud_service.py` (asset
      inexistente, portfolio inexistente, cantidad/precio ≤0, alta
      correcta). Verificado en vivo contra el backend real: migración
      con downgrade+upgrade en la misma corrida, servidor levantado en el
      puerto 8001 (no pisar el proceso preexistente del 8000, que había
      quedado con código viejo de antes de v3 — ver nota abajo), POST
      sin `portfolio_id` → 422, con portfolio inexistente → 404, alta
      válida → 201. 155 tests backend + 23 frontend en verde, `tsc
      --noEmit` y build de producción limpios.

      **Nota operativa:** el proceso de `uvicorn` en el puerto 8000
      seguía sirviendo código de antes del commit de v3 (le faltaba
      `/api/portfolios`) y no se pudo identificar/matar de forma
      confiable desde esta sesión — `netstat`/`Get-NetTCPConnection`
      reportaban un PID dueño del socket que `Get-Process`/`taskkill`
      decían que no existía. Si alguien tiene una terminal propia con
      ese proceso, reiniciarlo a mano; si no, probablemente sea un
      proceso zombie de Windows que un reinicio de la máquina resuelve.
- [ ] 3. **Resumen ejecutivo.** Nueva vista (o sección en Portfolio) que
      junta: alertas disparadas, tesis con status `objetivo_alcanzado` o
      `stop_tocado`, y fuentes con frescura `nunca`/`corrió pero no
      promovió nada` — todo ya calculado por los servicios existentes
      (`alert_service`, `thesis_service`, `freshness_service`), esto es
      composición de UI, no cálculo nuevo.

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
