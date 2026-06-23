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


def compare_assets(db: Session, tickers: list[str]) -> list[dict]:
    """Side-by-side comparison of key metrics for selected tickers."""
    from app.analytics.returns import daily_returns, total_return
    from app.analytics.risk import max_drawdown, sharpe_ratio, volatility

    result = []
    all_series = price_series_by_ticker(db, [t.upper() for t in tickers])

    for ticker in tickers:
        t = ticker.upper()
        series = all_series.get(t)
        if series is None or series.size < 2:
            result.append({"ticker": t, "data_points": 0})
            continue

        closes = series.to_numpy(dtype=float)
        rets = daily_returns(closes)
        recent = closes[-21:] if closes.size >= 21 else closes

        result.append({
            "ticker": t,
            "data_points": int(series.size),
            "latest_price": round(float(closes[-1]), 2),
            "total_return": round(float(total_return(closes) * 100), 2),
            "return_1m": round(float(total_return(recent) * 100), 2),
            "volatility": round(float(volatility(rets) * 100), 2),
            "max_drawdown": round(float(max_drawdown(closes) * 100), 2),
            "sharpe": round(float(sharpe_ratio(rets)), 2),
        })

    return result
