# Fase 0 — Scaffold: que el esqueleto respire antes de poner músculo

## El problema que resolvía

Antes de escribir una sola métrica financiera quería una cosa: un esqueleto que
**corra de punta a punta**. Backend que responde, frontend que pinta el theme
correcto, y —clave— los mecanismos con los que voy a *verificar* cada fase
funcionando desde el día cero. No quería descubrir en la Fase 4 que no podía
sacarle una captura a la UI para compararla contra el spec.

## La decisión de arquitectura: la raíz del repo ES el proyecto

El BRIEF describe un árbol que arranca en `/clara`. La tentación era crear
`CLARA/clara/backend`, pero eso anida una carpeta redundante. Mapeé la raíz del
BRIEF a la raíz del repo: `backend/` y `frontend/` cuelgan directo. Un nivel
menos de ruido para quien clone esto.

Separé backend y frontend como dos proyectos con su propio gestor de
dependencias (venv de Python / `package.json`), nunca dependencias globales.
Es lo que pide trabajar desatendido sin ensuciar la máquina.

El backend se construye con una **application factory** (`create_app()`) en vez
de un `app` global suelto. Parece un detalle, pero es lo que hace que el test de
humo pueda instanciar la app limpia, sin estado compartido. `main.py` queda
delgado a propósito: a medida que entren routers (portfolio, métricas, noticias)
se incluyen acá y nada más.

El theme visual vive en **un solo lugar de verdad**: `tailwind.config.js` define
los tokens (`bg`, `surface`, `accent`, `gain`, `loss`, `warn`) y `theme.ts` los
espeja para los contextos JS donde Tailwind no llega (props de Recharts). Un
cambio de color es un cambio en un archivo.

## La alternativa que descarté: Tailwind v4

Tailwind v4 movió la configuración a CSS y un plugin de Vite. Más nuevo, sí, pero
el BRIEF habla explícitamente de "theme tokens" como config, y v3.4 con
`tailwind.config.js` es el camino estable y legible para eso. Elegí aburrido y
predecible sobre novedoso.

## El antes / después de esta fase

- **Antes:** carpeta vacía.
- **Después:** `uvicorn` levanta y `GET /api/health` responde
  `{"status":"ok","app":"CLARA",...}`. `npm run dev` muestra el sidebar vertical
  con las 5 pestañas, el theme dark aplicado (#0D0D0F de fondo, cards #1C1C1E,
  acento iOS azul), y la pestaña Portfolio confirma en verde que habla con el
  backend a través del proxy de Vite. `pytest` y `vitest` en verde.

## La piedra en el zapato: la captura de pantalla

El loop de verificación de diseño depende de poder sacarle un screenshot a la
app corriendo. La herramienta de preview integrada se colgaba a los 30s, tanto
contra el dev server como contra el build estático. En vez de pelearme con eso,
encontré el camino que sí funciona en este entorno (controlar un Chrome real
apuntando al dev server) y lo dejé anotado para no volver a tropezar en cada
fase de UI. Verificar tus mecanismos de verificación es, también, trabajo de
Fase 0.

## Criterios de aceptación cumplidos

- [x] `uvicorn app.main:app` arranca; `/api/health` responde 200.
- [x] `npm run dev` muestra el shell con las 5 pestañas y el theme correcto.
- [x] `pytest` verde (smoke del health endpoint).
- [x] `vitest` verde (render del shell + las 5 pestañas).
- [x] Captura de la UI obtenida y comparada contra el spec.
