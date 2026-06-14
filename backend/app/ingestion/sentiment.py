"""Sentiment scoring.

Uses VADER (lexicon + rule based) for English text — it returns a `compound`
score already normalized to [-1, 1], which is exactly our convention. For
Spanish financial text VADER is weak; the intended production path there is an
LLM classifier (see ADR 0005). We don't ship a half-working VADER-on-Spanish.

The analyzer is constructed once (loading the lexicon is the expensive part).
"""

from __future__ import annotations

from functools import lru_cache

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@lru_cache(maxsize=1)
def _analyzer() -> SentimentIntensityAnalyzer:
    return SentimentIntensityAnalyzer()


def score(text: str) -> float:
    """Sentiment in [-1, 1]. Empty text -> 0.0 (neutral)."""
    if not text or not text.strip():
        return 0.0
    return round(float(_analyzer().polarity_scores(text)["compound"]), 4)


def label(sentiment: float) -> str:
    """Bucket a score into positive / neutral / negative for display."""
    if sentiment >= 0.05:
        return "positive"
    if sentiment <= -0.05:
        return "negative"
    return "neutral"
