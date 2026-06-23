# Fase 9 — Chatbot IA + página de activo individual

## El problema que resolvía

El portfolio mostraba números, pero no contestaba preguntas. Un inversor mira
una posición y quiere saber "¿qué pasa con este activo?", "¿cuáles son los
riesgos?". Eso requiere cruzar datos del portfolio con conocimiento general
del activo — exactamente lo que un LLM hace bien si le das contexto.

## Lo que se hizo

**Página de detalle por activo.** Cada ticker en la tabla de posiciones ahora
lleva a `/asset/:ticker` con un resumen: precio, rendimiento, volatilidad,
drawdown, posición del usuario, sentimiento de noticias. Es el "brief" del
activo antes de hablar con el chatbot.

**Chatbot de análisis fundamental.** El servicio `chat_service` arma un
contexto estructurado con los datos reales del portfolio (precio, retorno,
volatilidad, P&L, noticias recientes con sentimiento) y se lo pasa al LLM
como system prompt. El chatbot responde en español, con estructura, y nunca
da consejo financiero personalizado — ofrece marcos de decisión.

**Fallback estático.** Sin API key configurada, el chatbot genera un análisis
regla-base con los mismos datos: tipo de instrumento, performance, posición,
sentimiento. No es conversacional pero es útil y siempre funciona.

## Decisiones

- El contexto se arma en el backend, no en el frontend. El LLM recibe datos
  ya calculados, no hace queries.
- System prompt explícito con reglas de conducta (no dar recomendaciones de
  compra/venta, ser honesto sobre incertidumbre).
- El endpoint `/api/chat/fundamental` recibe el historial completo de mensajes
  para mantener el contexto conversacional.
