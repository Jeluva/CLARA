# CLARA — Cartera, Lectura, Análisis, Riesgo y Acción

> Una **mesa de análisis de portfolio** local. No un tracker de saldos: una
> herramienta que cruza tus posiciones con métricas de riesgo, noticias,
> sentimiento, macro y transcripciones de analistas, para responder rápido las
> preguntas que un inversor realmente se hace.

CLARA está construida como pieza de portfolio profesional: demuestra **data
engineering** (arquitectura medallion, data quality, ingestión idempotente) y
**análisis de datos** (métricas financieras testeadas y verificadas a mano) al
mismo tiempo, con una UI dark/minimalista con fundamentos de iOS.

---

## El problema

La información de mis activos vivía dispersa: el precio en un lado, la noticia
en otro, el análisis del que sigo en YouTube en un tercero, y el riesgo real de
mi cartera —volatilidad, drawdown, concentración, correlaciones— en ningún lado.
Perdía contexto y, a veces, oportunidades. CLARA junta todo eso en una sola
superficie y hace las cuentas que importan, con tests que prueban que están bien.

## La solución: cinco pestañas, cada una responde una pregunta

| Pestaña | Pregunta que responde |
|---|---|
| **Portfolio** | ¿Cómo está parada mi cartera hoy? Valor, P&L, riesgo, vs. benchmark. |
| **Noticias & Sentimiento** | ¿Qué pasa con mis activos y cómo afecta mi tesis? |
| **Research** | ¿Estoy realmente diversificado? ¿Qué dice el técnico? |
| **Macro** | ¿Cómo está el contexto (índices, dólar, riesgo país, tasas)? |
| **Ingreso de datos** | ¿Cómo cargo y edito posiciones y fuentes? |

> **Capturas:** ver `docs/screenshots/` (se agregan en la revisión) y la
> bitácora narrativa por fase en `docs/devlog/`.

## La arquitectura (por qué está pensada, no improvisada)

```
FUENTES            INGESTIÓN              ALMACENAMIENTO         SERVING
yfinance      ┐                           BRONZE (crudo)         API REST
News API      ├─▶  clients (mock)    ──▶  SILVER (limpio)   ──▶  (FastAPI)  ──▶  React
YouTube       │   + data quality          GOLD (métricas)
macro / FX    ┘   + cuarentena
```

- **Medallion (bronze → silver → gold):** el dato crudo se guarda tal cual
  (reprocesable sin volver a la fuente); silver son las entidades limpias y
  tipadas con claves naturales `UNIQUE` (ingestión idempotente); gold son las
  métricas agregadas.
- **Data quality con cuarentena:** checks declarativos (precio > 0, fecha no
  futura, ticker existe, sentimiento ∈ [-1, 1]) corren antes de promover a
  silver. Lo que falla va a una tabla `quarantine` con el motivo — **nunca se
  descarta en silencio**.
- **Capa de servicio:** único puente entre la base y la capa de analytics. Los
  routers quedan finos; analytics queda puro (funciones sin DB, triviales de
  testear).
- **SQLite en dev → Postgres en prod:** mismo esquema, solo cambia el connection
  string. Migraciones con Alembic.

Decisiones de diseño documentadas como ADRs en `docs/adr/`.

## Lo que más puntúa: las métricas están testeadas y verificadas a mano

Cada función de cálculo financiero tiene un test cuyo valor esperado fue
**calculado por fuera** (no contra la propia función): rendimiento total y
time-weighted, volatilidad anualizada, max drawdown, Sharpe, beta, exposición,
concentración Herfindahl, correlaciones, SMA y RSI. Más un test de integración
sobre datos reales del seed (`beta(SPY, SPY) ≈ 1` como canario de alineación
temporal).

```
backend:  73 tests (pytest)      frontend:  7 tests (vitest)
```

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic, Alembic,
  APScheduler, pandas/numpy, VADER (sentimiento).
- **Frontend:** React + Vite + TypeScript + Tailwind + Recharts.
- **DB:** SQLite (dev) / Postgres (prod, vía Docker).

## Cómo correrlo

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate                 # Windows  (bash: source venv/Scripts/activate)
pip install -r requirements.txt
alembic upgrade head                  # crea el esquema medallion
python -m app.storage.seed_cli        # portfolio de ejemplo + precios/noticias (mock)
uvicorn app.main:app --reload         # http://127.0.0.1:8000  (Swagger en /docs)
```

### Frontend
```bash
cd frontend
npm install
npm run dev                           # http://localhost:5180
```

### Tests
```bash
cd backend  && venv\Scripts\python -m pytest
cd frontend && npm test
```

### Postgres (prod, opcional)
```bash
docker compose up -d                  # levanta Postgres 16
# luego, con DATABASE_URL apuntando a Postgres:
cd backend && alembic upgrade head && python -m app.storage.seed_cli
```

## Qué es real y qué es mock (honestidad de alcance)

Durante el desarrollo **toda la ingestión usa mocks determinísticos** (sin red):

- **Precios:** movimiento browniano geométrico con semilla fija por ticker.
- **Noticias/transcripciones:** fixtures en inglés, con sentimiento **calculado
  por VADER de verdad** (no hardcodeado).
- **Macro:** valores realistas pero estáticos, declarados como mock en la propia
  pestaña.

Cada fuente sigue el patrón `fetch → bronze → validar → promover`, así que
enchufar la fuente real (yfinance, News API, `youtube-transcript-api`, dolarapi)
es reemplazar **solo el paso de fetch**, sin tocar el resto del pipeline.

## Estado del proyecto

- [x] **Fase 0 — Scaffold** · app corre de punta a punta, theme aplicado.
- [x] **Fase 1 — Capa de datos** · medallion + data quality + cuarentena + seed.
- [x] **Fase 2 — Analytics** · métricas verificadas a mano (47 tests).
- [x] **Fase 3 — API** · service layer + routers + test de integración.
- [x] **Fase 4 — Portfolio** · dashboard principal con datos reales.
- [x] **Fase 5 — Ingreso de datos** · CRUD end-to-end + ingestión idempotente.
- [x] **Fase 6 — Noticias & Sentimiento** · ingestión + VADER + pestaña.
- [x] **Fase 7 — Research & Macro** · correlación, indicadores, macro.
- [x] **Fase 8 — Pulido** · scheduler, Docker, README, cierre.

## Qué aprendí / qué sigue

- **Verificar a mano paga:** mi primer test de Sharpe falló por un error *mío* en
  la multiplicación del comentario, no en la función. Un test contra la propia
  función nunca lo habría atrapado.
- **El dato sucio no se tira, se audita:** la cuarentena convirtió "validación"
  en "observabilidad del pipeline".
- **Honestidad de alcance:** mock declarado + ADR que explica el camino real vale
  más que un gráfico bonito que no significa nada.
- **Próximos pasos (V2):** fuentes reales enchufadas, sentimiento en español con
  un LLM, serie de P&L realizada que respete el timing de entrada (ver
  `docs/adr/0003`), y correlaciones sobre precios reales.

---

*Bitácora de desarrollo en `docs/devlog/` · decisiones de arquitectura en
`docs/adr/` · resumen final en `docs/devlog/RESUMEN.md`.*
