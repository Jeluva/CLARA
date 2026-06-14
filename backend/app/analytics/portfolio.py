"""Portfolio orchestration: turn positions + prices into snapshots and series.

Pure functions over plain inputs (no DB). The service layer maps silver rows
into `PositionInput`s and price Series, calls these, then layers the risk/return
metrics on top of the resulting portfolio value series.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PositionInput:
    ticker: str
    quantity: float
    avg_cost: float
    latest_price: float
    sector: str = "Unknown"
    country: str = "Unknown"
    currency: str = "USD"


@dataclass(frozen=True)
class PositionSnapshot:
    ticker: str
    quantity: float
    avg_cost: float
    latest_price: float
    market_value: float
    cost_basis: float
    pnl: float
    pnl_pct: float
    weight: float
    sector: str
    country: str
    currency: str


def build_position_snapshots(
    positions: Sequence[PositionInput],
) -> list[PositionSnapshot]:
    """Compute market value, P&L and portfolio weight for each position."""
    market_values = [p.quantity * p.latest_price for p in positions]
    total_mv = sum(market_values)

    snapshots: list[PositionSnapshot] = []
    for p, mv in zip(positions, market_values):
        cost_basis = p.quantity * p.avg_cost
        pnl = mv - cost_basis
        pnl_pct = (mv / cost_basis - 1.0) if cost_basis != 0 else 0.0
        weight = (mv / total_mv) if total_mv != 0 else 0.0
        snapshots.append(
            PositionSnapshot(
                ticker=p.ticker,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                latest_price=p.latest_price,
                market_value=mv,
                cost_basis=cost_basis,
                pnl=pnl,
                pnl_pct=pnl_pct,
                weight=weight,
                sector=p.sector,
                country=p.country,
                currency=p.currency,
            )
        )
    return snapshots


def portfolio_value_series(
    quantities: Mapping[str, float],
    price_series: Mapping[str, pd.Series],
) -> pd.Series:
    """Total portfolio value over time = sum_t( quantity_i * price_i(t) ).

    `price_series` maps ticker -> a pandas Series indexed by date. Series are
    aligned on their dates (outer join), forward-filled to carry the last known
    price across gaps, and rows before every holding has a price are dropped.
    Only tickers present in `quantities` contribute.
    """
    columns = {
        ticker: series
        for ticker, series in price_series.items()
        if ticker in quantities
    }
    if not columns:
        return pd.Series(dtype=float)

    frame = pd.DataFrame(columns).sort_index().ffill()
    # Drop leading rows where some held asset has no price yet.
    frame = frame.dropna()
    if frame.empty:
        return pd.Series(dtype=float)

    qty_vector = pd.Series(quantities)
    # Weight each column by its quantity and sum across assets per date.
    value = frame.mul(qty_vector, axis=1).sum(axis=1)
    return value
