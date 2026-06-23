"""Sentiment scoring.

Two strategies:
  1. VADER (lexicon + rule based) — fast, no API key, good for English.
  2. LLM classifier — for Spanish or when higher accuracy is needed. Uses the
     same provider chain as the chatbot (Groq → Qwen → Gemini → Anthropic).
     Falls back to VADER if no LLM is available or the call fails.

The analyzer is constructed once (loading the lexicon is the expensive part).
See ADR 0005 for the rationale.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger("clara.sentiment")


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


def _is_spanish(text: str) -> bool:
    """Heuristic: text contains common Spanish words."""
    spanish_markers = r"\b(el|la|los|las|del|una|con|por|que|para|como|más|pero|sobre|este|esta|según)\b"
    matches = len(re.findall(spanish_markers, text.lower()))
    words = len(text.split())
    return words > 3 and matches / max(words, 1) > 0.08


def _score_llm(text: str) -> float | None:
    """Score sentiment via LLM. Returns float in [-1, 1] or None on failure."""
    from app.config import settings

    prompt = (
        "Puntuá el sentimiento financiero del siguiente texto con un número "
        "entre -1.0 (muy negativo) y 1.0 (muy positivo). Respondé SOLO con "
        "el número, sin explicación.\n\n"
        f"Texto: {text[:500]}"
    )

    providers = []
    if settings.groq_api_key:
        providers.append(("Groq", settings.groq_api_key, "https://api.groq.com/openai/v1", settings.groq_model))
    if settings.qwen_api_key:
        providers.append(("Qwen", settings.qwen_api_key, "https://dashscope.aliyuncs.com/compatible-mode/v1", settings.qwen_model))

    for name, api_key, base_url, model in providers:
        try:
            from openai import OpenAI, APIStatusError
            client = OpenAI(api_key=api_key, base_url=base_url)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            raw = (resp.choices[0].message.content or "").strip()
            value = float(re.search(r"-?[01]\.?\d*", raw).group())
            return max(-1.0, min(1.0, round(value, 4)))
        except (APIStatusError, AttributeError, ValueError, Exception) as exc:
            logger.debug("LLM sentiment (%s) failed: %s", name, exc)
            continue

    return None


def score(text: str) -> float:
    """Sentiment in [-1, 1]. Empty text -> 0.0 (neutral).

    Uses LLM for Spanish text if a provider is configured; falls back to VADER.
    """
    if not text or not text.strip():
        return 0.0
    if _is_spanish(text):
        llm_score = _score_llm(text)
        if llm_score is not None:
            return llm_score
    return round(float(_analyzer().polarity_scores(text)["compound"]), 4)


def label(sentiment: float) -> str:
    """Bucket a score into positive / neutral / negative for display."""
    if sentiment >= 0.05:
        return "positive"
    if sentiment <= -0.05:
        return "negative"
    return "neutral"
