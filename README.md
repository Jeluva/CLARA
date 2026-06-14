# CLARA — Cartera, Lectura, Análisis, Riesgo y Acción

Una **mesa de análisis de portfolio** local: no un tracker de saldos, sino una
herramienta que cruza tus posiciones con métricas de riesgo, noticias,
sentimiento, macro y transcripciones de analistas, para responder rápido las
preguntas que un inversor realmente se hace.

> Proyecto en construcción, desarrollado por fases. Ver `docs/devlog/` para la
> bitácora narrativa y `docs/adr/` para las decisiones de arquitectura.

## Por qué existe

La información de mis activos vivía dispersa: el precio en un lado, la noticia en
otro, el análisis del que sigo en YouTube en un tercero, y el riesgo real de mi
cartera en ningún lado. CLARA junta todo eso en una sola superficie y calcula lo
que importa: exposición, riesgo y rendimiento, con las cuentas hechas y
testeadas.

## Pestañas (cada una responde una pregunta)

| Pestaña | Pregunta |
|---|---|
| Portfolio | ¿Cómo está parada mi cartera hoy? |
| Noticias & Sentimiento | ¿Qué pasa con mis activos y cómo afecta mi tesis? |
| Research | ¿Qué dicen los datos técnicos y las correlaciones? |
| Macro | ¿Cómo está el contexto (índices, tasas, dólar)? |
| Ingreso de datos | ¿Cómo cargo y edito posiciones y fuentes? |

## Arquitectura

```
FUENTES          INGESTIÓN         ALMACENAMIENTO        SERVING
yfinance     ┐                     BRONZE (crudo)        API REST
News API     ├─▶  clients     ──▶  SILVER (limpio)  ──▶  (FastAPI)  ──▶  React
YouTube      │   + data quality    GOLD (métricas)
macro        ┘
```

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic. SQLite en dev,
  Postgres-ready en prod (solo cambia el connection string).
- **Frontend:** React + Vite + TypeScript + Tailwind + Recharts. Tema dark
  minimalista con fundamentos de iOS.
- **Datos:** arquitectura medallion (bronze/silver/gold) + cuarentena de data
  quality. Métricas financieras con tests unitarios verificados a mano.

## Cómo correrlo

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate           # Windows (en bash: source venv/Scripts/activate)
pip install -r requirements.txt
alembic upgrade head            # crea el esquema (medallion + portfolio)
python -m app.storage.seed_cli  # siembra portfolio de ejemplo + precios (mock)
uvicorn app.main:app --reload   # http://127.0.0.1:8000  (docs en /docs)
```

### Frontend
```bash
cd frontend
npm install
npm run dev                     # http://localhost:5180
```

### Tests
```bash
cd backend && venv\Scripts\python -m pytest
cd frontend && npm test
```

## Estado

- [x] **Fase 0 — Scaffold:** app corre de punta a punta, theme aplicado, las 5
      pestañas navegables, tests y verificación visual funcionando.
- [x] **Fase 1 — Capa de datos:** esquema medallion (bronze/silver/gold),
      checks de data quality con cuarentena, migraciones Alembic y seed
      idempotente con portfolio de ejemplo + ~1 año de precios.
- [x] **Fase 2 — Analytics:** motor de métricas (rendimiento, volatilidad,
      drawdown, Sharpe, beta, exposición, Herfindahl, correlación) como
      funciones puras, 47 tests con valores verificados a mano.
- [ ] Fase 3 — API
- [ ] Fase 4 — Pestaña Portfolio
- [ ] Fase 5 — Ingreso de datos
- [ ] Fase 6 — Noticias & Sentimiento
- [ ] Fase 7 — Research y Macro
- [ ] Fase 8 — Pulido + publicación
