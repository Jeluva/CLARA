"""Macro service: reference indices, FX and rates.

Real mode (USE_MOCK_SOURCES=false): fetches live data on every request.
- Indices (S&P 500, Nasdaq 100, Merval) → yfinance
- Dólar MEP / CCL / Blue → dolarapi.com (public, no key)
- US 10Y yield → yfinance (^TNX)
- BADLAR → static (no free public source; swap in BCRA API if needed)

Mock mode: static placeholder values (original behaviour).

The shape of each card is identical either way, so the UI never changes.
"""

from __future__ import annotations

import httpx

from app.config import settings

# ---------------------------------------------------------------------------
# Static mock (always available as fallback)
# ---------------------------------------------------------------------------

_MOCK: list[dict] = [
    {"key": "spx",          "label": "S&P 500",      "value": 5634.6,   "unit": "pts", "change_pct": 0.42,  "group": "Índices"},
    {"key": "merval",       "label": "Merval",        "value": 1648320.0,"unit": "pts", "change_pct": -0.85, "group": "Índices"},
    {"key": "nasdaq",       "label": "Nasdaq 100",    "value": 20114.3,  "unit": "pts", "change_pct": 0.61,  "group": "Índices"},
    {"key": "mep",          "label": "Dólar MEP",     "value": 1278.5,   "unit": "ARS", "change_pct": 0.55,  "group": "Dólar"},
    {"key": "ccl",          "label": "Dólar CCL",     "value": 1305.0,   "unit": "ARS", "change_pct": 0.73,  "group": "Dólar"},
    {"key": "blue",         "label": "Dólar Blue",    "value": 1270.0,   "unit": "ARS", "change_pct": -0.39, "group": "Dólar"},
    {"key": "riesgo_pais",  "label": "Riesgo País",   "value": 642.0,    "unit": "pb",  "change_pct": -1.84, "group": "Tasas & Riesgo"},
    {"key": "ust10y",       "label": "US 10Y",        "value": 4.21,     "unit": "%",   "change_pct": 0.12,  "group": "Tasas & Riesgo"},
    {"key": "badlar",       "label": "BADLAR",        "value": 38.5,     "unit": "%",   "change_pct": -0.25, "group": "Tasas & Riesgo"},
]


# ---------------------------------------------------------------------------
# Real fetchers
# ---------------------------------------------------------------------------

def _fetch_yf_card(symbol: str, key: str, label: str, unit: str, group: str) -> dict | None:
    """Fetch last two closes from yfinance and compute day change."""
    try:
        import yfinance as yf
        hist = yf.download(symbol, period="5d", progress=False, auto_adjust=True)
        if hist.empty or len(hist) < 2:
            return None
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None
        vals = closes.to_numpy(dtype=float).flatten()
        prev, last = float(vals[-2]), float(vals[-1])
        change_pct = ((last - prev) / prev * 100) if prev else 0.0
        return {
            "key": key,
            "label": label,
            "value": round(last, 2),
            "unit": unit,
            "change_pct": round(change_pct, 2),
            "group": group,
        }
    except Exception:
        return None


def _fetch_dolarapi() -> dict[str, dict]:
    """Return a dict keyed by casa name from dolarapi.com."""
    try:
        resp = httpx.get("https://dolarapi.com/v1/dolares", timeout=5)
        resp.raise_for_status()
        result: dict[str, dict] = {}
        for item in resp.json():
            casa = (item.get("casa") or "").lower()
            result[casa] = item
        return result
    except Exception:
        return {}


def _dolar_card(data: dict, casa: str, key: str, label: str, mock_value: float) -> dict:
    item = data.get(casa, {})
    value = float(item.get("venta") or mock_value)
    compra = float(item.get("compra") or value)
    change_pct = ((value - compra) / compra * 100) if compra else 0.0
    return {
        "key": key,
        "label": label,
        "value": round(value, 1),
        "unit": "ARS",
        "change_pct": round(change_pct, 2),
        "group": "Dólar",
    }


def _fetch_live() -> list[dict]:
    cards: list[dict] = []

    # Indices
    for symbol, key, label in [
        ("^GSPC",  "spx",    "S&P 500"),
        ("^MERV",  "merval", "Merval"),
        ("^NDX",   "nasdaq", "Nasdaq 100"),
    ]:
        card = _fetch_yf_card(symbol, key, label, "pts", "Índices")
        cards.append(card or next(m for m in _MOCK if m["key"] == key))

    # Dólar
    dolar = _fetch_dolarapi()
    cards.append(_dolar_card(dolar, "bolsa",           "mep",  "Dólar MEP", 1278.5))
    cards.append(_dolar_card(dolar, "contadoconliqui", "ccl",  "Dólar CCL", 1305.0))
    cards.append(_dolar_card(dolar, "blue",            "blue", "Dólar Blue", 1270.0))

    # Tasas & Riesgo
    # Riesgo país: no free REST endpoint; keep mock until BCRA/ambito integration.
    cards.append(next(m for m in _MOCK if m["key"] == "riesgo_pais"))

    ust = _fetch_yf_card("^TNX", "ust10y", "US 10Y", "%", "Tasas & Riesgo")
    cards.append(ust or next(m for m in _MOCK if m["key"] == "ust10y"))

    # BADLAR: no free machine-readable source; keep mock.
    cards.append(next(m for m in _MOCK if m["key"] == "badlar"))

    return cards


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_macro() -> list[dict]:
    if settings.use_mock_sources:
        return list(_MOCK)
    try:
        return _fetch_live()
    except Exception:
        return list(_MOCK)
