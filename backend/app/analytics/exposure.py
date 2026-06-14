"""Exposure and concentration metrics.

Exposure groups market value by a category (sector/country/currency) and
normalizes to weights. Concentration summarizes how lopsided those weights are:
top-N share and the Herfindahl-Hirschman Index (HHI).
"""

from __future__ import annotations

from collections.abc import Sequence


def exposure_by_category(
    items: Sequence[tuple[str, float]],
) -> dict[str, float]:
    """Sum market values per category and return normalized weights.

    `items` is a list of (category, market_value). Returns {category: weight},
    weights summing to 1.0 (empty / zero-total -> empty dict).
    """
    totals: dict[str, float] = {}
    for category, value in items:
        totals[category] = totals.get(category, 0.0) + float(value)
    grand_total = sum(totals.values())
    if grand_total <= 0:
        return {}
    return {cat: val / grand_total for cat, val in totals.items()}


def herfindahl_index(weights: Sequence[float]) -> float:
    """Herfindahl-Hirschman Index = sum of squared weights.

    Ranges from 1/n (perfectly diversified across n) to 1.0 (single holding).
    Higher = more concentrated.
    """
    arr = [float(w) for w in weights]
    if not arr:
        return 0.0
    return sum(w * w for w in arr)


def top_n_concentration(weights: Sequence[float], n: int = 3) -> float:
    """Combined weight of the n largest positions."""
    arr = sorted((float(w) for w in weights), reverse=True)
    return sum(arr[:n])
