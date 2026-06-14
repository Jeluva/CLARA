"""Read-side helpers for price data: latest prices and aligned price series."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.storage.models.silver import Asset, Price


def latest_prices(db: Session) -> dict[str, float]:
    """Map ticker -> most recent close. Assets without prices are omitted."""
    # Subquery: latest date per asset.
    latest_date = (
        select(Price.asset_id, func.max(Price.date).label("max_date"))
        .group_by(Price.asset_id)
        .subquery()
    )
    rows = db.execute(
        select(Asset.ticker, Price.close)
        .join(Price, Price.asset_id == Asset.id)
        .join(
            latest_date,
            (latest_date.c.asset_id == Price.asset_id)
            & (latest_date.c.max_date == Price.date),
        )
    ).all()
    return {ticker: close for ticker, close in rows}


def price_series_by_ticker(
    db: Session, tickers: list[str] | None = None
) -> dict[str, pd.Series]:
    """Map ticker -> pd.Series of close indexed by date (ascending).

    If `tickers` is given, only those are loaded; otherwise all assets.
    """
    query = (
        select(Asset.ticker, Price.date, Price.close)
        .join(Price, Price.asset_id == Asset.id)
        .order_by(Asset.ticker, Price.date)
    )
    if tickers is not None:
        query = query.where(Asset.ticker.in_(tickers))

    rows = db.execute(query).all()
    if not rows:
        return {}

    frame = pd.DataFrame(rows, columns=["ticker", "date", "close"])
    frame["date"] = pd.to_datetime(frame["date"])
    series: dict[str, pd.Series] = {}
    for ticker, group in frame.groupby("ticker"):
        series[str(ticker)] = pd.Series(
            group["close"].to_numpy(),
            index=pd.DatetimeIndex(group["date"]),
            name=str(ticker),
        )
    return series
