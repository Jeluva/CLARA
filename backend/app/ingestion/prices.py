"""Price ingestion: real data via yfinance, with a mock fallback.

Real mode (USE_MOCK_SOURCES=false): downloads daily closes from Yahoo Finance
for every asset in silver. Argentine equities/bonds use the `.BA` suffix.
Fills all missing business days up to today through the standard medallion path
(bronze → promote). Idempotent: the dedupe key `{ticker}:{date}` absorbs retries.

Mock mode (USE_MOCK_SOURCES=true): deterministic random walk, no network.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.quality.promote import PromotionResult, promote_bronze
from app.storage.models.bronze import BronzeRecord
from app.storage.models.silver import Asset, Price

# Tickers that trade on BCBA — yfinance requires the .BA suffix.
_BA_TICKERS = {"GGAL", "YPFD", "PAMP", "BMA", "LOMA", "TECO2", "TXAR",
               "AL30", "GD30", "AL35", "AE38"}


def _yf_symbol(ticker: str) -> str:
    return f"{ticker}.BA" if ticker.upper() in _BA_TICKERS else ticker.upper()


def _today() -> date:
    return datetime.now(timezone.utc).date()


# ---------------------------------------------------------------------------
# Real ingestion
# ---------------------------------------------------------------------------

def _run_real_price_ingestion(db: Session) -> PromotionResult:
    import yfinance as yf

    assets = db.execute(select(Asset)).scalars().all()
    if not assets:
        return PromotionResult(promoted=0, quarantined=0)

    today = _today()

    # Find the latest stored date per asset to avoid re-downloading everything.
    latest_map: dict[str, date] = {}
    rows = db.execute(
        select(Asset.ticker, func.max(Price.date).label("max_date"))
        .join(Price, Price.asset_id == Asset.id)
        .group_by(Asset.ticker)
    ).all()
    for ticker, max_date in rows:
        if max_date:
            latest_map[ticker] = max_date

    for asset in assets:
        ticker = asset.ticker.upper()
        symbol = _yf_symbol(ticker)
        start = latest_map.get(ticker, today - timedelta(days=365))
        # Download from the day after the last stored date.
        fetch_from = start + timedelta(days=1)
        if fetch_from > today:
            continue

        try:
            hist = yf.download(
                symbol,
                start=fetch_from.isoformat(),
                end=(today + timedelta(days=1)).isoformat(),
                progress=False,
                auto_adjust=True,
            )
        except Exception:
            continue

        if hist.empty:
            continue

        for idx_date, row in hist.iterrows():
            day = idx_date.date() if hasattr(idx_date, "date") else idx_date
            close_val = float(row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"])
            if close_val <= 0:
                continue
            dedupe = f"{ticker}:{day.isoformat()}"
            already = db.execute(
                select(BronzeRecord).where(
                    BronzeRecord.source_table == "prices",
                    BronzeRecord.dedupe_key == dedupe,
                )
            ).first()
            if already is not None:
                continue
            db.add(BronzeRecord(
                source_table="prices",
                source="yfinance",
                dedupe_key=dedupe,
                payload=json.dumps({
                    "ticker": ticker,
                    "date": day.isoformat(),
                    "close": round(close_val, 4),
                    "source": "yfinance",
                }),
            ))

    db.commit()
    return promote_bronze(db)


# ---------------------------------------------------------------------------
# Mock ingestion (original implementation, kept as fallback)
# ---------------------------------------------------------------------------

def _next_business_day(d: date) -> date:
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def _stepped_price(ticker: str, day: date, last_close: float) -> float:
    seed = sum(ord(c) for c in ticker) + day.toordinal()
    frac = (math.sin(seed) + 1) / 2
    step = (frac - 0.5) * 0.04
    return round(max(0.01, last_close * (1 + step)), 4)


def run_mock_price_ingestion(db: Session) -> PromotionResult:
    today = _today()
    latest = (
        select(Price.asset_id, func.max(Price.date).label("max_date"))
        .group_by(Price.asset_id)
        .subquery()
    )
    rows = db.execute(
        select(Asset.ticker, Price.date, Price.close)
        .join(Price, Price.asset_id == Asset.id)
        .join(latest, (latest.c.asset_id == Price.asset_id) & (latest.c.max_date == Price.date))
    ).all()

    for ticker, last_date, last_close in rows:
        close = last_close
        day = _next_business_day(last_date)
        while day <= today:
            close = _stepped_price(ticker, day, close)
            dedupe = f"{ticker}:{day.isoformat()}"
            already = db.execute(
                select(BronzeRecord).where(
                    BronzeRecord.source_table == "prices",
                    BronzeRecord.dedupe_key == dedupe,
                )
            ).scalar_one_or_none()
            if already is None:
                db.add(BronzeRecord(
                    source_table="prices",
                    source="mock-live",
                    dedupe_key=dedupe,
                    payload=json.dumps({
                        "ticker": ticker,
                        "date": day.isoformat(),
                        "close": close,
                        "source": "mock-live",
                    }),
                ))
            day = _next_business_day(day)
    db.commit()
    return promote_bronze(db)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_price_ingestion(db: Session) -> PromotionResult:
    if settings.use_mock_sources:
        return run_mock_price_ingestion(db)
    return _run_real_price_ingestion(db)
