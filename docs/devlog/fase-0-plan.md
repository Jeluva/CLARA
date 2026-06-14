# Fase 0 — Plan: Scaffold

## Objetivo
Dejar el esqueleto del proyecto corriendo de punta a punta: backend FastAPI que
responde, frontend React+Vite+TS+Tailwind con el theme dark aplicado y el shell
de las 5 pestañas (vacías) navegables desde un sidebar vertical. Verificar que
los mecanismos de verificación (pytest, vitest, screenshot del frontend)
funcionan antes de empezar las fases pesadas.

## Archivos que voy a tocar
- `.gitignore` (hecho)
- `backend/`: `requirements.txt`, `app/main.py`, `app/__init__.py`,
  `app/api/`, `app/config.py`, `.env.example`, `tests/test_smoke.py`,
  `pytest.ini`/`pyproject.toml`.
- `frontend/`: scaffold Vite (React+TS), Tailwind config con tokens del theme,
  `src/styles/theme.ts`, `src/components/Sidebar.tsx`, `src/pages/*` (5 stubs),
  `src/App.tsx`, router, `src/lib/api.ts`, `src/test/smoke.test.tsx`.
- `docs/devlog/fase-0.md`, `README.md` inicial.

## Decisiones
- Raíz del repo = raíz `/clara` del BRIEF: creo `backend/` y `frontend/`
  directos (sin anidar `clara/` redundante).
- Uso `python` (3.12.10) + venv local del proyecto; nada global.
- Sidebar con React Router para navegar entre las 5 pestañas.
- Theme como tokens centralizados (Tailwind config + CSS variables).

## Criterio de aceptación
- `uvicorn app.main:app` arranca y `GET /api/health` responde `{status: ok}`.
- `npm run dev` levanta el frontend, se ve el sidebar con las 5 pestañas y el
  theme dark correcto (#0D0D0F fondo, cards #1C1C1E, acento #0A84FF).
- `pytest` verde (smoke test del health endpoint).
- `vitest` verde (smoke test del render del shell).
- Puedo sacar un screenshot del frontend corriendo (valida el loop de diseño).
