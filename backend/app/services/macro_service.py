"""Macro service: reference indices, FX and rates.

MOCK DATA: these are realistic but static placeholder values, not live feeds.
AUTORUN forbids live network calls; the real implementation plugs into
yfinance (indices), dolarapi (MEP/CCL) and a public source for country risk —
documented in the README. The shape (value + variation) is what the UI consumes,
so swapping in a real source is a drop-in.
"""

from __future__ import annotations

# (key, label, value, unit, change_pct, group)
_MACRO: list[dict] = [
    {"key": "spx", "label": "S&P 500", "value": 5634.6, "unit": "pts",
     "change_pct": 0.42, "group": "Índices"},
    {"key": "merval", "label": "Merval", "value": 1648320.0, "unit": "pts",
     "change_pct": -0.85, "group": "Índices"},
    {"key": "nasdaq", "label": "Nasdaq 100", "value": 20114.3, "unit": "pts",
     "change_pct": 0.61, "group": "Índices"},
    {"key": "mep", "label": "Dólar MEP", "value": 1278.5, "unit": "ARS",
     "change_pct": 0.55, "group": "Dólar"},
    {"key": "ccl", "label": "Dólar CCL", "value": 1305.0, "unit": "ARS",
     "change_pct": 0.73, "group": "Dólar"},
    {"key": "blue", "label": "Dólar Blue", "value": 1270.0, "unit": "ARS",
     "change_pct": -0.39, "group": "Dólar"},
    {"key": "riesgo_pais", "label": "Riesgo País", "value": 642.0, "unit": "pb",
     "change_pct": -1.84, "group": "Tasas & Riesgo"},
    {"key": "ust10y", "label": "US 10Y", "value": 4.21, "unit": "%",
     "change_pct": 0.12, "group": "Tasas & Riesgo"},
    {"key": "badlar", "label": "BADLAR", "value": 38.5, "unit": "%",
     "change_pct": -0.25, "group": "Tasas & Riesgo"},
]


def get_macro() -> list[dict]:
    """Return the macro indicator cards (mock)."""
    return list(_MACRO)
