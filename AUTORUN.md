# AUTORUN.md — Protocolo de desarrollo autónomo de CLARA

> Pegá este prompt a Claude Code (en auto mode) una vez que el repo tenga `BRIEF.md`.
> Mensaje de arranque sugerido:
> *"Leé `BRIEF.md` y `AUTORUN.md`. Vas a trabajar de forma autónoma según el protocolo de AUTORUN. Empezá por la Fase 0 y avanzá solo, sin pedirme permiso, hasta terminar todas las fases o hasta un bloqueo real. Yo voy a revisar tu trabajo cuando vuelva."*

## Modo de trabajo

Trabajás de forma autónoma y continua. Tu objetivo es completar TODAS las fases del
proyecto definido en `BRIEF.md` sin intervención humana, dejando el trabajo
documentado y commiteado para que pueda revisarlo cuando vuelva.

NO me pidas permiso ni confirmación entre fases. Avanzá solo. Solo te detenés ante
un "bloqueo real" según se define más abajo.

## Ciclo por fase (repetir para cada fase del BRIEF, Fase 0 a Fase 8)

Para cada fase, ejecutá este ciclo completo antes de pasar a la siguiente:

1. **Plan**: escribí en `/docs/devlog/fase-N-plan.md` un plan corto: objetivo,
   archivos que vas a tocar, criterio de aceptación.
2. **Implementar**: escribí el código de la fase, respetando el BRIEF (stack,
   capas, diseño visual, esquema de datos).
3. **Auto-revisión de código** (obligatoria): revisá tu propio código como un
   reviewer senior. Listá problemas con severidad (alta/media/baja): funciones sin
   test, manejo de errores faltante, valores hardcodeados, violaciones de
   separación de capas, credenciales expuestas. Arreglá TODOS los de severidad
   alta y media antes de seguir.
4. **Tests**: corré la suite (pytest + vitest). Si algo falla, arreglalo. Las
   funciones de cálculo financiero DEBEN tener test que verifique el resultado
   contra un caso conocido calculado a mano.
5. **Verificación funcional**: levantá la app. Si la fase tocó UI, sacá un
   screenshot y compará contra el spec de diseño del BRIEF (colores, tipografía,
   densidad, jerarquía). Listá hasta 5 diferencias y corregilas.
6. **Devlog**: escribí `/docs/devlog/fase-N.md` con tono narrativo en primera
   persona: qué problema resolvías, qué decisión de arquitectura tomaste y por
   qué, qué alternativa descartaste, y un antes/después. Esto es contenido para
   publicar después, escribilo bien.
7. **Commit**: `git add -A && git commit` con un mensaje descriptivo y narrativo
   (ej. "Fase 2: motor de métricas de riesgo con Sharpe/drawdown testeados").
8. **Avanzar**: pasá a la fase siguiente automáticamente.

## Reglas de seguridad para trabajo desatendido

- NUNCA borres archivos o ramas fuera del scope de la fase actual. Si algo
  "estorba", movelo o renombralo, no lo borres.
- NUNCA uses credenciales reales ni busques API keys en el sistema. Las fuentes
  externas que requieran key van con MOCK realista, documentado en el README.
- NO corras la ingestión real contra internet (noticias/YouTube/precios en vivo).
  Toda la ingestión durante este run usa datos mock o fixtures locales. La
  conexión a fuentes reales la voy a hacer yo, presente.
- Mantené todo el trabajo DENTRO del directorio del proyecto.
- Commiteá seguido. Cada commit es mi red de seguridad.
- No instales dependencias globales del sistema; usá el entorno del proyecto
  (venv / package.json).

## Definición de "bloqueo real" (cuándo SÍ detenerte)

Detenete y escribí `/docs/BLOCKED.md` con el detalle SOLO si:
- Una decisión de producto es genuinamente ambigua y elegir mal arruinaría el
  trabajo posterior (documentá las opciones y tu recomendación).
- Necesitás una API key o recurso externo que no tengo cómo mockear.
- Un test falla y después de 3 intentos distintos no lográs arreglarlo
  (documentá qué probaste).
- Detectás que una acción podría ser destructiva o irreversible y dudás.

En `BLOCKED.md`: qué te frenó, qué opciones ves, qué necesitás de mí, y qué
fases pudiste completar igual antes del bloqueo. Después seguí con cualquier
otra fase que NO dependa del bloqueo, si existe.

## Al terminar todas las fases

Escribí `/docs/devlog/RESUMEN.md`:
- Qué quedó construido y funcionando (con criterios de aceptación cumplidos).
- Qué quedó pendiente o mockeado y por qué.
- Lista de decisiones de arquitectura tomadas (para convertir en ADRs).
- Próximos pasos sugeridos.
- Capturas finales de cada pestaña.

Dejá la app en estado "corre con un comando" y el README final escrito como
narrativa (problema → solución → arquitectura → qué aprendí). Hacé el commit
final y quedate en idle.

## Higiene de logs para storytelling

A medida que avanzás, los mensajes de commit y las entradas de devlog son la
materia prima del contenido que voy a publicar. Escribilos pensando en eso:
claros, con la decisión y el trade-off explícitos, en primera persona.
