"""Research service: technical indicators for a selected asset."""

from __future__ import annotations

import math

from sqlalchemy.orm import Session

from app.analytics.indicators import macd, rsi, sma
from app.services.market_data import price_series_by_ticker


def _clean(value: float) -> float | None:
    """JSON-safe: NaN -> None."""
    return None if math.isnan(value) else round(float(value), 4)


def get_indicators(db: Session, ticker: str) -> dict:
    """Price series with SMA(20), SMA(50) and RSI(14) for one ticker.

    Returns the last ~120 points to keep the payload light for the chart.
    """
    series = price_series_by_ticker(db, [ticker.upper()]).get(ticker.upper())
    if series is None or series.empty:
        return {"ticker": ticker.upper(), "points": []}

    closes = series.to_numpy(dtype=float)
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    rsi14 = rsi(closes, 14)
    macd_line, signal_line, hist = macd(closes)

    points = [
        {
            "date": idx.date().isoformat(),
            "close": round(float(closes[i]), 4),
            "sma20": _clean(sma20[i]),
            "sma50": _clean(sma50[i]),
            "rsi": _clean(rsi14[i]),
            "macd": _clean(macd_line[i]),
            "macd_signal": _clean(signal_line[i]),
            "macd_hist": _clean(hist[i]),
        }
        for i, idx in enumerate(series.index)
    ]
    return {"ticker": ticker.upper(), "points": points[-120:]}
