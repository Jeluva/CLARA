"""Per-asset summary for the asset detail page."""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.returns import daily_returns, total_return
from app.analytics.risk import max_drawdown, volatility
from app.services import news_service
from app.services.market_data import price_series_by_ticker
from app.services.portfolio_service import _position_inputs
from app.storage.models.silver import Asset


def get_asset_summary(db: Session, ticker: str) -> dict | None:
    ticker = ticker.upper()
    asset = db.execute(
        select(Asset).where(Asset.ticker == ticker)
    ).scalar_one_or_none()
    if asset is None:
        return None

    out: dict = {
        "ticker": asset.ticker,
        "name": asset.name,
        "asset_class": asset.asset_class,
        "sector": asset.sector,
        "country": asset.country,
        "currency": asset.currency,
        "latest_price": None,
        "total_return": None,
        "volatility": None,
        "max_drawdown": None,
        "position": None,
        "news_count": 0,
        "avg_sentiment": None,
    }

    series = price_series_by_ticker(db, [ticker]).get(ticker)
    if series is not None and series.size >= 2:
        closes = series.to_numpy(dtype=float)
        rets = daily_returns(closes)
        out["latest_price"] = round(float(closes[-1]), 4)
        out["total_return"] = round(total_return(closes), 6)
        out["volatility"] = round(volatility(rets), 6)
        out["max_drawdown"] = round(max_drawdown(closes), 6)

    pos = next((p for p in _position_inputs(db) if p.ticker == ticker), None)
    if pos is not None:
        mv = pos.quantity * pos.latest_price
        cost = pos.quantity * pos.avg_cost
        out["position"] = {
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost,
            "market_value": round(mv, 2),
            "pnl": round(mv - cost, 2),
            "pnl_pct": round((mv / cost - 1) if cost else 0.0, 6),
        }

    news = news_service.list_news(db, ticker)
    out["news_count"] = len(news)
    if news:
        out["avg_sentiment"] = round(float(np.mean([n.sentiment for n in news])), 4)

    return out
