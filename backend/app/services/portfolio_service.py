"""Portfolio service: reads silver, runs analytics, returns plain results.

This is the bridge layer. It owns the only knowledge of *how* portfolio numbers
are assembled from the tables, so routers and analytics each stay simple.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import risk
from app.analytics.correlation import correlation_matrix
from app.analytics.exposure import (
    exposure_by_category,
    herfindahl_index,
    top_n_concentration,
)
from app.analytics.portfolio import (
    PositionInput,
    PositionSnapshot,
    build_position_snapshots,
    portfolio_value_series,
)
from app.analytics.returns import daily_returns, total_return
from app.services.market_data import latest_prices, price_series_by_ticker
from app.storage.models.silver import Asset, Position

BENCHMARK_TICKER = "SPY"


@dataclass
class PortfolioOverview:
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    daily_pnl: float
    daily_pnl_pct: float
    positions: list[PositionSnapshot]


@dataclass
class RiskMetrics:
    volatility: float
    sharpe: float
    max_drawdown: float
    beta: float
    cumulative_return: float
    top3_concentration: float
    herfindahl: float


def _held_positions(db: Session) -> list[tuple[Asset, float, float]]:
    """Aggregate open positions per asset -> (asset, quantity, avg_cost).

    Multiple open lots of the same asset are merged with a weighted average cost.
    """
    rows = (
        db.execute(
            select(Position, Asset)
            .join(Asset, Asset.id == Position.asset_id)
            .where(Position.status == "open")
        )
        .all()
    )
    agg: dict[int, dict] = {}
    for position, asset in rows:
        bucket = agg.setdefault(
            asset.id, {"asset": asset, "qty": 0.0, "cost": 0.0}
        )
        bucket["qty"] += position.quantity
        bucket["cost"] += position.quantity * position.avg_cost

    result: list[tuple[Asset, float, float]] = []
    for bucket in agg.values():
        qty = bucket["qty"]
        avg_cost = bucket["cost"] / qty if qty else 0.0
        result.append((bucket["asset"], qty, avg_cost))
    return result


def _position_inputs(db: Session) -> list[PositionInput]:
    prices = latest_prices(db)
    inputs: list[PositionInput] = []
    for asset, qty, avg_cost in _held_positions(db):
        price = prices.get(asset.ticker)
        if price is None:
            continue  # no price -> can't value it; skip (see ADR/roadmap)
        inputs.append(
            PositionInput(
                ticker=asset.ticker,
                quantity=qty,
                avg_cost=avg_cost,
                latest_price=price,
                sector=asset.sector,
                country=asset.country,
                currency=asset.currency,
            )
        )
    return inputs


def _portfolio_value_series(db: Session) -> pd.Series:
    """Value series of currently-held assets (excludes the benchmark)."""
    inputs = _position_inputs(db)
    quantities = {p.ticker: p.quantity for p in inputs}
    if not quantities:
        return pd.Series(dtype=float)
    series = price_series_by_ticker(db, list(quantities.keys()))
    return portfolio_value_series(quantities, series)


def get_portfolio_overview(db: Session) -> PortfolioOverview:
    snapshots = build_position_snapshots(_position_inputs(db))
    total_value = sum(s.market_value for s in snapshots)
    total_cost = sum(s.cost_basis for s in snapshots)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_value / total_cost - 1.0) if total_cost else 0.0

    # Daily P&L from the last two points of the value series.
    value_series = _portfolio_value_series(db)
    daily_pnl = 0.0
    daily_pnl_pct = 0.0
    if value_series.size >= 2:
        prev, curr = float(value_series.iloc[-2]), float(value_series.iloc[-1])
        daily_pnl = curr - prev
        daily_pnl_pct = (curr / prev - 1.0) if prev else 0.0

    return PortfolioOverview(
        total_value=total_value,
        total_cost=total_cost,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        positions=snapshots,
    )


def get_risk_metrics(db: Session) -> RiskMetrics:
    value_series = _portfolio_value_series(db)
    values = value_series.to_numpy(dtype=float)
    port_returns = daily_returns(values)

    # Beta vs benchmark: align portfolio returns with SPY returns by date.
    beta_value = 0.0
    bench = price_series_by_ticker(db, [BENCHMARK_TICKER]).get(BENCHMARK_TICKER)
    if bench is not None and value_series.size >= 2:
        aligned = pd.concat(
            [value_series.rename("port"), bench.rename("bench")], axis=1
        ).dropna()
        if len(aligned) >= 3:
            p_ret = daily_returns(aligned["port"].to_numpy(dtype=float))
            b_ret = daily_returns(aligned["bench"].to_numpy(dtype=float))
            beta_value = risk.beta(p_ret, b_ret)

    weights = [s.weight for s in build_position_snapshots(_position_inputs(db))]

    return RiskMetrics(
        volatility=risk.volatility(port_returns),
        sharpe=risk.sharpe_ratio(port_returns),
        max_drawdown=risk.max_drawdown(values),
        beta=beta_value,
        cumulative_return=total_return(values),
        top3_concentration=top_n_concentration(weights, n=3),
        herfindahl=herfindahl_index(weights),
    )


def get_exposure(db: Session) -> dict[str, dict[str, float]]:
    snapshots = build_position_snapshots(_position_inputs(db))
    return {
        "sector": exposure_by_category(
            [(s.sector, s.market_value) for s in snapshots]
        ),
        "country": exposure_by_category(
            [(s.country, s.market_value) for s in snapshots]
        ),
        "currency": exposure_by_category(
            [(s.currency, s.market_value) for s in snapshots]
        ),
    }


def get_history(db: Session) -> list[dict]:
    """Cumulative-return series of the portfolio vs the benchmark, aligned."""
    value_series = _portfolio_value_series(db)
    if value_series.size < 1:
        return []

    bench = price_series_by_ticker(db, [BENCHMARK_TICKER]).get(BENCHMARK_TICKER)
    frame = pd.DataFrame({"port": value_series})
    if bench is not None:
        frame["bench"] = bench
    frame = frame.sort_index().ffill().dropna()
    if frame.empty:
        return []

    port_cum = frame["port"] / frame["port"].iloc[0] - 1.0
    out: list[dict] = []
    bench_cum = None
    if "bench" in frame:
        bench_cum = frame["bench"] / frame["bench"].iloc[0] - 1.0
    for i, idx in enumerate(frame.index):
        out.append(
            {
                "date": idx.date().isoformat(),
                "portfolio": round(float(port_cum.iloc[i]), 6),
                "benchmark": (
                    round(float(bench_cum.iloc[i]), 6)
                    if bench_cum is not None
                    else None
                ),
            }
        )
    return out


def get_realized_history(db: Session) -> list[dict]:
    """P&L realizado: solo cuenta cada activo desde su opened_at.

    A diferencia de get_history (que aplica tenencias actuales a toda la
    historia), esta serie refleja el timing real de las decisiones de entrada.
    """
    positions = _held_positions(db)
    if not positions:
        return []

    tickers = [a.ticker for a, _, _ in positions]
    all_series = price_series_by_ticker(db, tickers)

    opened_dates: dict[str, pd.Timestamp] = {}
    costs: dict[str, float] = {}
    quantities: dict[str, float] = {}
    for asset, qty, avg_cost in positions:
        rows = db.execute(
            select(Position.opened_at)
            .where(Position.asset_id == asset.id, Position.status == "open")
        ).scalars().all()
        earliest = min(rows) if rows else None
        if earliest is not None:
            opened_dates[asset.ticker] = pd.Timestamp(earliest).normalize()
        costs[asset.ticker] = avg_cost
        quantities[asset.ticker] = qty

    # Build a DataFrame with prices, masking each ticker before its opened_at
    frames: dict[str, pd.Series] = {}
    for ticker in tickers:
        series = all_series.get(ticker)
        if series is None:
            continue
        opened = opened_dates.get(ticker)
        if opened is not None:
            series = series[series.index >= opened]
        frames[ticker] = series

    if not frames:
        return []

    price_df = pd.DataFrame(frames).sort_index()

    out: list[dict] = []
    for idx in price_df.index:
        cost = 0.0
        value = 0.0
        for ticker in tickers:
            if ticker not in price_df.columns:
                continue
            price = price_df.at[idx, ticker]
            if pd.isna(price):
                continue
            qty = quantities[ticker]
            cost += qty * costs[ticker]
            value += qty * float(price)
        if cost == 0:
            continue
        pnl_pct = value / cost - 1.0
        out.append({
            "date": idx.date().isoformat(),
            "realized_pnl": round(pnl_pct, 6),
        })
    return out


def get_correlation(db: Session) -> dict:
    """Correlation matrix of daily returns across held assets (NaN -> 0)."""
    inputs = _position_inputs(db)
    tickers = [p.ticker for p in inputs]
    series = price_series_by_ticker(db, tickers)
    returns = {
        t: daily_returns(s.to_numpy(dtype=float)) for t, s in series.items()
    }
    matrix = correlation_matrix(returns)
    if matrix.empty:
        return {"tickers": [], "matrix": []}
    matrix = matrix.replace({np.nan: 0.0})
    return {
        "tickers": list(matrix.columns),
        "matrix": matrix.round(4).to_numpy().tolist(),
    }
