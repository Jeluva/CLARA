"""USD/ARS spot rate for normalizing multi-currency portfolio values.

Positions and prices are entered/quoted in their native currency (CEDEARs and
US equities in USD, Argentine equities/bonds in ARS). Aggregating a portfolio
across currencies needs a common basis — this converts ARS amounts to USD
using the MEP rate from dolarapi.com (same source as the Macro tab).

Spot-rate only: historical series (portfolio evolution chart, correlation,
beta) still use raw native-currency prices, so an ARS-denominated ticker's
return there reflects its peso-basis move, not its USD-basis move. Full
historical FX normalization is a follow-up, not implemented here.
"""

from __future__ import annotations

import httpx

_FALLBACK_MEP_RATE = 1300.0  # used only if dolarapi.com is unreachable


def usd_ars_rate() -> float:
    try:
        resp = httpx.get("https://dolarapi.com/v1/dolares/bolsa", timeout=5)
        resp.raise_for_status()
        value = float(resp.json().get("venta") or 0)
        return value if value > 0 else _FALLBACK_MEP_RATE
    except Exception:
        return _FALLBACK_MEP_RATE


def to_usd(amount: float, currency: str) -> float:
    if currency.upper() != "ARS":
        return amount
    return amount / usd_ars_rate()
