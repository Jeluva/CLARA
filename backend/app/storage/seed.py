"""Seed the database with a realistic example portfolio.

MOCK DATA NOTICE: prices are generated as a deterministic seeded random walk
(geometric Brownian motion), NOT real market data. AUTORUN forbids live network
calls during development, so this stands in for the real price ingestion that
lands in later phases. The shape (drift, volatility) is plausible per asset so
the analytics layer has meaningful numbers to chew on.

Reference data (assets, positions, transactions) is written straight to silver —
it's user-entered, not source-ingested. Prices flow through bronze → promotion
to exercise the full medallion + data-quality pipeline end to end.

The whole thing is idempotent: re-running upserts on natural keys, never
duplicates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.quality.promote import promote_bronze
from app.storage.models.bronze import BronzeRecord
from app.storage.models.silver import Asset, Position, Transaction

# Reference date for the seed. Kept explicit (not "today") so the dataset is
# fully reproducible regardless of when the seed runs.
SEED_END_DATE = date(2026, 6, 12)  # a Friday
TRADING_DAYS = 252  # ~1 year of business days


@dataclass
class SeedAsset:
    ticker: str
    name: str
    asset_class: str
    sector: str
    country: str
    currency: str
    start_price: float
    annual_drift: float  # expected annual return
    annual_vol: float  # annualized volatility
    # Position to open (None => benchmark only, no holding). qty, avg_cost, days_ago
    holding: tuple[float, float, int] | None = field(default=None)


# A diversified, Argentina-flavoured book: US tech via CEDEARs, local equities,
# a sovereign bond, plus SPY as the benchmark (held: no position).
SEED_ASSETS: list[SeedAsset] = [
    SeedAsset("AAPL", "Apple Inc.", "cedear", "Technology", "USA", "USD",
              190.0, 0.18, 0.28, holding=(40, 165.0, 240)),
    SeedAsset("MSFT", "Microsoft Corp.", "cedear", "Technology", "USA", "USD",
              410.0, 0.16, 0.25, holding=(15, 350.0, 300)),
    SeedAsset("NVDA", "NVIDIA Corp.", "cedear", "Technology", "USA", "USD",
              120.0, 0.35, 0.50, holding=(60, 70.0, 200)),
    SeedAsset("KO", "Coca-Cola Co.", "cedear", "Consumer Staples", "USA", "USD",
              62.0, 0.07, 0.16, holding=(80, 58.0, 220)),
    SeedAsset("GGAL", "Grupo Financiero Galicia", "equity", "Financials",
              "Argentina", "ARS", 48.0, 0.22, 0.45, holding=(50, 30.0, 180)),
    SeedAsset("YPFD", "YPF S.A.", "equity", "Energy", "Argentina", "ARS",
              38.0, 0.25, 0.55, holding=(45, 22.0, 160)),
    SeedAsset("AL30", "Bono Soberano AL30D", "bond", "Government", "Argentina",
              "USD", 62.0, 0.10, 0.20, holding=(2000, 48.0, 260)),
    SeedAsset("SPY", "SPDR S&P 500 ETF", "etf", "Index", "USA", "USD",
              520.0, 0.10, 0.16, holding=None),  # benchmark
]


def _business_days(end: date, count: int) -> list[date]:
    """The `count` most recent business days ending on/before `end`."""
    days: list[date] = []
    cursor = end
    while len(days) < count:
        if cursor.weekday() < 5:  # Mon-Fri
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


def _stable_seed(ticker: str) -> int:
    """Deterministic per-ticker RNG seed (independent of PYTHONHASHSEED)."""
    return sum(ord(c) * (i + 1) for i, c in enumerate(ticker)) + 1000


def _simulate_prices(asset: SeedAsset, days: list[date]) -> list[float]:
    """Geometric Brownian motion: deterministic given the ticker."""
    rng = np.random.default_rng(_stable_seed(asset.ticker))
    n = len(days)
    dt = 1.0 / TRADING_DAYS
    mu, sigma = asset.annual_drift, asset.annual_vol
    shocks = rng.standard_normal(n)
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * shocks
    log_returns[0] = 0.0  # anchor first day at start_price
    prices = asset.start_price * np.exp(np.cumsum(log_returns))
    return [round(float(p), 4) for p in prices]


def _upsert_asset(db: Session, sa: SeedAsset) -> Asset:
    existing = db.execute(
        select(Asset).where(Asset.ticker == sa.ticker)
    ).scalar_one_or_none()
    if existing is None:
        asset = Asset(
            ticker=sa.ticker,
            name=sa.name,
            asset_class=sa.asset_class,
            sector=sa.sector,
            country=sa.country,
            currency=sa.currency,
        )
        db.add(asset)
        db.flush()
        return asset
    existing.name = sa.name
    existing.asset_class = sa.asset_class
    existing.sector = sa.sector
    existing.country = sa.country
    existing.currency = sa.currency
    return existing


def seed_database(db: Session) -> dict[str, int]:
    """Idempotently seed assets, positions, transactions and prices.

    Returns a small summary of what was written (useful for the seed CLI/tests).
    """
    days = _business_days(SEED_END_DATE, TRADING_DAYS)

    for sa in SEED_ASSETS:
        asset = _upsert_asset(db, sa)

        # Position + matching opening transaction (only if there's a holding).
        if sa.holding is not None:
            qty, avg_cost, days_ago = sa.holding
            opened_at = datetime.combine(
                SEED_END_DATE - timedelta(days=days_ago), datetime.min.time()
            )
            has_position = db.execute(
                select(Position).where(Position.asset_id == asset.id)
            ).scalar_one_or_none()
            if has_position is None:
                db.add(
                    Position(
                        asset_id=asset.id,
                        quantity=qty,
                        avg_cost=avg_cost,
                        opened_at=opened_at,
                        status="open",
                    )
                )
                db.add(
                    Transaction(
                        asset_id=asset.id,
                        type="buy",
                        quantity=qty,
                        price=avg_cost,
                        fee=round(qty * avg_cost * 0.005, 2),
                        executed_at=opened_at,
                    )
                )

        # Prices → bronze (raw), to be promoted into silver below.
        prices = _simulate_prices(sa, days)
        for d, close in zip(days, prices):
            dedupe = f"{sa.ticker}:{d.isoformat()}"
            already = db.execute(
                select(BronzeRecord).where(
                    BronzeRecord.source_table == "prices",
                    BronzeRecord.dedupe_key == dedupe,
                )
            ).scalar_one_or_none()
            if already is not None:
                continue
            payload = json.dumps(
                {
                    "ticker": sa.ticker,
                    "date": d.isoformat(),
                    "close": close,
                    "source": "mock",
                }
            )
            db.add(
                BronzeRecord(
                    source_table="prices",
                    source="mock",
                    dedupe_key=dedupe,
                    payload=payload,
                )
            )

    db.commit()

    promo = promote_bronze(db)

    return {
        "assets": len(db.execute(select(Asset)).scalars().all()),
        "positions": len(db.execute(select(Position)).scalars().all()),
        "transactions": len(db.execute(select(Transaction)).scalars().all()),
        "prices_promoted": promo.promoted,
        "prices_quarantined": promo.quarantined,
    }
