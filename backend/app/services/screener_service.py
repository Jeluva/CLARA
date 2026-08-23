"""Screener: fundamentals + technicals side by side for every tracked asset,
so the user can filter for candidates instead of only analyzing what they
already picked (see docs/devlog/BACKLOG.md, v2 item 3)."""

from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.indicators import rsi, sma
from app.analytics.returns import total_return
from app.services.market_data import price_series_by_ticker
from app.storage.models.silver import Asset, Fundamentals


def _clean(value: float | None) -> float | None:
    """JSON-safe: None/NaN/inf -> None."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(numeric) or math.isinf(numeric) else round(numeric, 4)


def get_screener(db: Session) -> list[dict]:
    """One row per tracked asset: latest fundamentals snapshot plus
    price momentum (1-month return), RSI(14) and the SMA20/50 trend."""
    assets = db.execute(select(Asset)).scalars().all()
    if not assets:
        return []

    fundamentals_by_asset_id = {
        f.asset_id: f for f in db.execute(select(Fundamentals)).scalars().all()
    }
    series = price_series_by_ticker(db, [a.ticker for a in assets])

    rows: list[dict] = []
    for asset in assets:
        fund = fundamentals_by_asset_id.get(asset.id)
        s = series.get(asset.ticker)

        latest_price = return_1m = rsi14 = trend = None
        if s is not None and s.size >= 2:
            closes = s.to_numpy(dtype=float)
            latest_price = _clean(closes[-1])
            recent = closes[-21:] if closes.size >= 21 else closes
            return_1m = _clean(total_return(recent) * 100)
            rsi_series = rsi(closes, 14)
            if rsi_series.size:
                rsi14 = _clean(rsi_series[-1])
            if closes.size >= 50:
                sma20, sma50 = sma(closes, 20)[-1], sma(closes, 50)[-1]
                if not (math.isnan(sma20) or math.isnan(sma50)):
                    trend = "alcista" if sma20 > sma50 else "bajista"

        rows.append({
            "ticker": asset.ticker,
            "name": asset.name,
            "asset_class": asset.asset_class,
            "sector": asset.sector,
            "country": asset.country,
            "currency": asset.currency,
            "latest_price": latest_price,
            "return_1m": return_1m,
            "rsi14": rsi14,
            "trend": trend,
            "pe_ratio": _clean(fund.pe_ratio) if fund else None,
            "forward_pe": _clean(fund.forward_pe) if fund else None,
            "pb_ratio": _clean(fund.pb_ratio) if fund else None,
            "dividend_yield": _clean(fund.dividend_yield) if fund else None,
            "revenue_growth": _clean(fund.revenue_growth) if fund else None,
            "roe": _clean(fund.roe) if fund else None,
        })
    return rows
