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
from app.services import fx_service
from app.services.market_data import latest_prices, price_series_by_ticker
from app.storage.models.silver import Asset, Position

BENCHMARK_TICKER = "SPY"

# Position-sizing guide (BACKLOG v2 item 7): default fraction of annualized
# volatility a single position may contribute, and the hard ceiling on how
# much of the portfolio one position can take regardless of how low its
# volatility is (relevant for bonds, whose vol can be near zero).
DEFAULT_RISK_BUDGET_PCT = 0.03
MAX_POSITION_WEIGHT = 0.25


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


@dataclass
class PositionSizeGuide:
    ticker: str
    current_price: float
    volatility: float
    risk_budget_pct: float
    risk_budget_amount: float
    portfolio_total_value: float
    target_amount: float
    target_weight_pct: float
    current_amount: float
    current_weight_pct: float
    delta_amount: float
    delta_quantity: float
    capped: bool
    max_weight_cap: float
    warnings: list[str]


@dataclass
class SimulationResult:
    ticker: str
    amount: float
    quantity_added: float
    already_held: bool
    new_weight: float
    total_value_before: float
    total_value_after: float
    top3_before: float
    top3_after: float
    herfindahl_before: float
    herfindahl_after: float
    correlation_to_portfolio: float | None
    exposure_before: dict[str, dict[str, float]]
    exposure_after: dict[str, dict[str, float]]
    warnings: list[str]


def _held_positions(
    db: Session, portfolio_id: int | None = None
) -> list[tuple[Asset, float, float]]:
    """Aggregate open positions per asset -> (asset, quantity, avg_cost).

    Multiple open lots of the same asset are merged with a weighted average cost.
    `portfolio_id=None` merges every portfolio (the "ver todas las posiciones
    en total" case from docs/devlog/BACKLOG.md v3 item 1) -- there's no
    separate aggregation path, it's just the no-filter query.
    """
    query = (
        select(Position, Asset)
        .join(Asset, Asset.id == Position.asset_id)
        .where(Position.status == "open")
    )
    if portfolio_id is not None:
        query = query.where(Position.portfolio_id == portfolio_id)
    rows = db.execute(query).all()
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


def _position_inputs(
    db: Session, portfolio_id: int | None = None
) -> list[PositionInput]:
    """Position inputs with prices normalized to USD.

    `avg_cost`/`latest_price` and downstream market values are always USD, so
    ARS-denominated holdings (GGAL, YPFD, sovereign bonds) aggregate correctly
    against USD ones instead of inflating totals with raw peso figures.
    `currency` keeps the asset's *native* currency for the exposure breakdown.
    """
    prices = latest_prices(db)
    held = _held_positions(db, portfolio_id)
    rate = (
        fx_service.usd_ars_rate()
        if any(asset.currency.upper() == "ARS" for asset, _, _ in held)
        else None
    )
    inputs: list[PositionInput] = []
    for asset, qty, avg_cost in held:
        price = prices.get(asset.ticker)
        if price is None:
            continue  # no price -> can't value it; skip (see ADR/roadmap)
        if asset.currency.upper() == "ARS" and rate:
            price = price / rate
            avg_cost = avg_cost / rate
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


def _portfolio_value_series(db: Session, portfolio_id: int | None = None) -> pd.Series:
    """Value series of currently-held assets (excludes the benchmark)."""
    inputs = _position_inputs(db, portfolio_id)
    quantities = {p.ticker: p.quantity for p in inputs}
    if not quantities:
        return pd.Series(dtype=float)
    series = price_series_by_ticker(db, list(quantities.keys()))
    return portfolio_value_series(quantities, series)


def get_portfolio_overview(
    db: Session, portfolio_id: int | None = None
) -> PortfolioOverview:
    snapshots = build_position_snapshots(_position_inputs(db, portfolio_id))
    total_value = sum(s.market_value for s in snapshots)
    total_cost = sum(s.cost_basis for s in snapshots)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_value / total_cost - 1.0) if total_cost else 0.0

    # Daily P&L from the last two points of the value series.
    value_series = _portfolio_value_series(db, portfolio_id)
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


def get_risk_metrics(db: Session, portfolio_id: int | None = None) -> RiskMetrics:
    value_series = _portfolio_value_series(db, portfolio_id)
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

    weights = [
        s.weight for s in build_position_snapshots(_position_inputs(db, portfolio_id))
    ]

    return RiskMetrics(
        volatility=risk.volatility(port_returns),
        sharpe=risk.sharpe_ratio(port_returns),
        max_drawdown=risk.max_drawdown(values),
        beta=beta_value,
        cumulative_return=total_return(values),
        top3_concentration=top_n_concentration(weights, n=3),
        herfindahl=herfindahl_index(weights),
    )


def get_exposure(
    db: Session, portfolio_id: int | None = None
) -> dict[str, dict[str, float]]:
    return _exposure_snapshot(
        build_position_snapshots(_position_inputs(db, portfolio_id))
    )


def get_history(db: Session, portfolio_id: int | None = None) -> list[dict]:
    """Cumulative-return series of the portfolio vs the benchmark, aligned."""
    value_series = _portfolio_value_series(db, portfolio_id)
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


def get_realized_history(db: Session, portfolio_id: int | None = None) -> list[dict]:
    """P&L realizado: solo cuenta cada activo desde su opened_at.

    A diferencia de get_history (que aplica tenencias actuales a toda la
    historia), esta serie refleja el timing real de las decisiones de entrada.
    """
    positions = _held_positions(db, portfolio_id)
    if not positions:
        return []

    tickers = [a.ticker for a, _, _ in positions]
    all_series = price_series_by_ticker(db, tickers)

    opened_dates: dict[str, pd.Timestamp] = {}
    costs: dict[str, float] = {}
    quantities: dict[str, float] = {}
    for asset, qty, avg_cost in positions:
        query = select(Position.opened_at).where(
            Position.asset_id == asset.id, Position.status == "open"
        )
        if portfolio_id is not None:
            query = query.where(Position.portfolio_id == portfolio_id)
        rows = db.execute(query).scalars().all()
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


def get_correlation(db: Session, portfolio_id: int | None = None) -> dict:
    """Correlation matrix of daily returns across held assets (NaN -> 0)."""
    inputs = _position_inputs(db, portfolio_id)
    tickers = [p.ticker for p in inputs]
    series = price_series_by_ticker(db, tickers)
    if not series:
        return {"tickers": [], "matrix": []}
    # Align on shared dates first: per-ticker histories differ in coverage.
    aligned = pd.concat(
        [s.rename(t) for t, s in series.items()], axis=1
    ).dropna()
    returns = {
        t: daily_returns(aligned[t].to_numpy(dtype=float)) for t in aligned.columns
    }
    matrix = correlation_matrix(returns)
    if matrix.empty:
        return {"tickers": [], "matrix": []}
    matrix = matrix.replace({np.nan: 0.0})
    return {
        "tickers": list(matrix.columns),
        "matrix": matrix.round(4).to_numpy().tolist(),
    }


def _exposure_snapshot(snapshots: list[PositionSnapshot]) -> dict[str, dict[str, float]]:
    return {
        "sector": exposure_by_category([(s.sector, s.market_value) for s in snapshots]),
        "country": exposure_by_category([(s.country, s.market_value) for s in snapshots]),
        "currency": exposure_by_category([(s.currency, s.market_value) for s in snapshots]),
    }


def simulate_purchase(
    db: Session, ticker: str, amount: float, portfolio_id: int | None = None
) -> SimulationResult:
    """"What if I buy this" — impact of a hypothetical purchase on
    concentration, exposure and diversification, without touching any
    position (see docs/devlog/BACKLOG.md, v2 item 5).

    `amount` is USD to invest. Raises ValueError (-> 404 at the router) when
    the ticker doesn't exist or has no price to value the trade with.
    """
    ticker = ticker.upper()
    if amount <= 0:
        raise ValueError("El monto a simular debe ser mayor a cero.")

    asset = db.execute(select(Asset).where(Asset.ticker == ticker)).scalar_one_or_none()
    if asset is None:
        raise ValueError(f"{ticker} no existe. Agregalo primero en Ingreso de datos.")

    prices = latest_prices(db)
    price = prices.get(ticker)
    if price is None:
        raise ValueError(f"Sin precio para {ticker}. Corré la ingestión de precios primero.")

    rate = fx_service.usd_ars_rate() if asset.currency.upper() == "ARS" else None
    price_usd = price / rate if rate else price
    quantity_added = amount / price_usd if price_usd else 0.0

    current_inputs = _position_inputs(db, portfolio_id)
    current_snapshots = build_position_snapshots(current_inputs)

    already_held = any(p.ticker == ticker for p in current_inputs)
    after_inputs: list[PositionInput] = []
    for p in current_inputs:
        if p.ticker == ticker:
            new_qty = p.quantity + quantity_added
            new_avg_cost = (
                p.quantity * p.avg_cost + quantity_added * price_usd
            ) / new_qty
            after_inputs.append(
                PositionInput(
                    ticker=p.ticker,
                    quantity=new_qty,
                    avg_cost=new_avg_cost,
                    latest_price=p.latest_price,
                    sector=p.sector,
                    country=p.country,
                    currency=p.currency,
                )
            )
        else:
            after_inputs.append(p)
    if not already_held:
        after_inputs.append(
            PositionInput(
                ticker=ticker,
                quantity=quantity_added,
                avg_cost=price_usd,
                latest_price=price_usd,
                sector=asset.sector,
                country=asset.country,
                currency=asset.currency,
            )
        )

    after_snapshots = build_position_snapshots(after_inputs)
    weights_before = [s.weight for s in current_snapshots]
    weights_after = [s.weight for s in after_snapshots]
    new_weight = next((s.weight for s in after_snapshots if s.ticker == ticker), 0.0)

    warnings: list[str] = []
    other_tickers = [p.ticker for p in current_inputs if p.ticker != ticker]
    correlation_to_portfolio: float | None = None
    if not other_tickers:
        warnings.append(
            "No hay otras posiciones para comparar correlación todavía."
        )
    else:
        weight_by_ticker = {s.ticker: s.weight for s in current_snapshots}
        series = price_series_by_ticker(db, other_tickers + [ticker])
        target_series = series.get(ticker)
        corrs: list[float] = []
        weights: list[float] = []
        if target_series is None or target_series.empty:
            warnings.append(f"Sin historial de precios para {ticker} todavía.")
        else:
            for other in other_tickers:
                held_series = series.get(other)
                if held_series is None:
                    continue
                aligned = pd.concat(
                    [target_series.rename("new"), held_series.rename("held")], axis=1
                ).dropna()
                if len(aligned) < 3:
                    continue
                new_ret = daily_returns(aligned["new"].to_numpy(dtype=float))
                held_ret = daily_returns(aligned["held"].to_numpy(dtype=float))
                if new_ret.size < 2 or held_ret.size < 2:
                    continue
                c = float(np.corrcoef(new_ret, held_ret)[0, 1])
                if not np.isnan(c):
                    corrs.append(c)
                    weights.append(weight_by_ticker.get(other, 0.0))
            if corrs:
                total_w = sum(weights) or 1.0
                correlation_to_portfolio = sum(
                    c * w for c, w in zip(corrs, weights)
                ) / total_w

    return SimulationResult(
        ticker=ticker,
        amount=amount,
        quantity_added=quantity_added,
        already_held=already_held,
        new_weight=new_weight,
        total_value_before=sum(s.market_value for s in current_snapshots),
        total_value_after=sum(s.market_value for s in after_snapshots),
        top3_before=top_n_concentration(weights_before, n=3),
        top3_after=top_n_concentration(weights_after, n=3),
        herfindahl_before=herfindahl_index(weights_before),
        herfindahl_after=herfindahl_index(weights_after),
        correlation_to_portfolio=correlation_to_portfolio,
        exposure_before=_exposure_snapshot(current_snapshots),
        exposure_after=_exposure_snapshot(after_snapshots),
        warnings=warnings,
    )


def get_position_size_guide(
    db: Session,
    ticker: str,
    risk_budget_pct: float = DEFAULT_RISK_BUDGET_PCT,
    portfolio_id: int | None = None,
) -> PositionSizeGuide:
    """How much of this asset the volatility-scaled risk budget suggests holding
    (see docs/devlog/BACKLOG.md, v2 item 7).

    Rule: target dollar allocation = (portfolio value * risk_budget_pct) /
    annualized volatility -- a higher-volatility asset gets a smaller slice
    for the same contribution to portfolio risk. `risk_budget_pct` is
    expressed in annualized-volatility units (not the stop-distance
    convention used by `theses.stop_loss`), and the result is capped at
    `MAX_POSITION_WEIGHT` of the portfolio so a very low-vol asset (e.g. a
    bond) doesn't get sized into an outsized concentration.

    Raises ValueError (-> 404 at the router) when the ticker doesn't exist or
    has no price series to compute volatility from.
    """
    ticker = ticker.upper()
    if risk_budget_pct <= 0:
        raise ValueError("El presupuesto de riesgo debe ser mayor a cero.")

    asset = db.execute(select(Asset).where(Asset.ticker == ticker)).scalar_one_or_none()
    if asset is None:
        raise ValueError(f"{ticker} no existe. Agregalo primero en Ingreso de datos.")

    series = price_series_by_ticker(db, [ticker]).get(ticker)
    if series is None or series.size < 2:
        raise ValueError(f"Sin precio para {ticker}. Corré la ingestión de precios primero.")

    closes = series.to_numpy(dtype=float)
    vol = risk.volatility(daily_returns(closes))

    # Same USD normalization as simulate_purchase: the series is in the
    # asset's native currency, but portfolio values (and therefore the
    # target amount) are always USD.
    rate = fx_service.usd_ars_rate() if asset.currency.upper() == "ARS" else None
    current_price = float(closes[-1]) / rate if rate else float(closes[-1])

    overview = get_portfolio_overview(db, portfolio_id)
    total_value = overview.total_value or 0.0
    risk_budget_amount = total_value * risk_budget_pct

    warnings: list[str] = []
    capped = False
    if vol <= 0:
        warnings.append(
            "Sin volatilidad calculable (historial muy corto o precio "
            "constante) — no se puede aplicar la guía."
        )
        target_amount = 0.0
    else:
        target_amount = risk_budget_amount / vol
        max_amount = total_value * MAX_POSITION_WEIGHT
        if total_value > 0 and target_amount > max_amount:
            target_amount = max_amount
            capped = True
            warnings.append(
                "El tamaño sugerido por volatilidad superaba el tope de "
                f"concentración ({MAX_POSITION_WEIGHT:.0%} de la cartera) y "
                "se limitó a ese tope."
            )

    if total_value == 0:
        warnings.append(
            "La cartera está vacía: esta guía necesita un valor de cartera "
            "existente contra el cual dimensionar el presupuesto de riesgo."
        )

    held = next(
        (p for p in _position_inputs(db, portfolio_id) if p.ticker == ticker), None
    )
    current_amount = held.quantity * held.latest_price if held else 0.0
    current_weight_pct = (current_amount / total_value) if total_value else 0.0
    target_weight_pct = (target_amount / total_value) if total_value else 0.0

    delta_amount = target_amount - current_amount
    delta_quantity = delta_amount / current_price if current_price else 0.0

    return PositionSizeGuide(
        ticker=ticker,
        current_price=round(current_price, 4),
        volatility=round(vol, 6),
        risk_budget_pct=risk_budget_pct,
        risk_budget_amount=round(risk_budget_amount, 2),
        portfolio_total_value=round(total_value, 2),
        target_amount=round(target_amount, 2),
        target_weight_pct=round(target_weight_pct, 6),
        current_amount=round(current_amount, 2),
        current_weight_pct=round(current_weight_pct, 6),
        delta_amount=round(delta_amount, 2),
        delta_quantity=round(delta_quantity, 6),
        capped=capped,
        max_weight_cap=MAX_POSITION_WEIGHT,
        warnings=warnings,
    )
