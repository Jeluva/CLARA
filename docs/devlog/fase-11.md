# Fase 11 — Ingestion conectada + chatbot multi-provider

## El problema que resolvía

El chatbot dependía de una sola API key. Si esa key tenía rate limit o el
usuario no la tenía, no había chatbot. Y la ingestión real necesitaba estar
conectada end-to-end para que el scheduler pudiera correrla automáticamente.

## Lo que se hizo

**Ingestion end-to-end.** Los tres pipelines (precios, noticias, transcripciones)
corren tanto desde el scheduler como desde el botón "forzar ingestión" en la
UI. El resultado muestra cuántos registros se promovieron y cuántos fueron a
cuarentena.

**Chatbot multi-provider con fallback en cadena.** Se implementó una cadena de
providers LLM con prioridad:

1. **Groq** (Llama 3.3 70B) — tier gratuito generoso, API compatible con OpenAI.
2. **Qwen** (DashScope) — tier gratuito, API compatible con OpenAI.
3. **Gemini** (Google) — tier gratuito.
4. **Anthropic** (Claude) — pago.
5. **Estático** — análisis regla-base, siempre disponible.

Cada provider usa `_reply_openai_compat` (Groq y Qwen comparten el mismo
código vía base_url). Si un provider devuelve 429 (rate limit) o 402, se
pasa al siguiente. Si no hay ninguna key configurada, el análisis estático
genera un reporte útil con los datos del portfolio.

## Decisiones

- Los providers OpenAI-compatibles comparten una sola función genérica. Agregar
  un nuevo provider es una función de 5 líneas.
- El frontend no sabe qué provider respondió — solo ve `configured: true/false`.
- El test del chatbot mockea las settings para forzar el path estático,
  independiente de qué keys tenga el entorno.
