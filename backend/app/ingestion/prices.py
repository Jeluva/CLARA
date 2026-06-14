"""Mock price ingestion: append the next business day for every asset.

Demonstrates the full medallion path from a single trigger: simulate a fetch,
write raw payloads to bronze, then promote through the data-quality checks into
silver. Idempotent — running it twice on the same day adds nothing (the bronze
dedupe key + the UNIQUE(asset_id, date) constraint absorb the repeat).

The "fetch" is a deterministic random step from each asset's last close, seeded
by (ticker, date), so there's no live network and results are reproducible.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.quality.promote import PromotionResult, promote_bronze
from app.storage.models.bronze import BronzeRecord
from app.storage.models.silver import Asset, Price


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _next_business_day(d: date) -> date:
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:  # skip Sat/Sun
        nxt += timedelta(days=1)
    return nxt


def _stepped_price(ticker: str, day: date, last_close: float) -> float:
    """Deterministic ~daily move from last close, seeded by (ticker, date)."""
    seed = sum(ord(c) for c in ticker) + day.toordinal()
    # Map seed to a pseudo-random step in roughly [-2%, +2%].
    frac = (math.sin(seed) + 1) / 2  # 0..1
    step = (frac - 0.5) * 0.04
    return round(max(0.01, last_close * (1 + step)), 4)


def run_mock_price_ingestion(db: Session) -> PromotionResult:
    """Catch each asset up to today: fill every missing business day's close.

    Walks from each asset's last stored date forward, one business day at a time,
    stopping at today (never the future — that's a data-quality rule, and we
    don't fabricate prices that don't exist yet). Idempotent: a second run on the
    same day finds nothing new to add.
    """
    today = _today()

    # Latest date + close per asset.
    latest = (
        select(Price.asset_id, func.max(Price.date).label("max_date"))
        .group_by(Price.asset_id)
        .subquery()
    )
    rows = db.execute(
        select(Asset.ticker, Price.date, Price.close)
        .join(Price, Price.asset_id == Asset.id)
        .join(
            latest,
            (latest.c.asset_id == Price.asset_id)
            & (latest.c.max_date == Price.date),
        )
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
                db.add(
                    BronzeRecord(
                        source_table="prices",
                        source="mock-live",
                        dedupe_key=dedupe,
                        payload=json.dumps(
                            {
                                "ticker": ticker,
                                "date": day.isoformat(),
                                "close": close,
                                "source": "mock-live",
                            }
                        ),
                    )
                )
            day = _next_business_day(day)
    db.commit()
    return promote_bronze(db)
