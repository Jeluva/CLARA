"""Pydantic response models for the API. Keep serialization explicit and typed."""

from __future__ import annotations

from pydantic import BaseModel


class PositionOut(BaseModel):
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


class PortfolioOverviewOut(BaseModel):
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    daily_pnl: float
    daily_pnl_pct: float
    positions: list[PositionOut]


class RiskMetricsOut(BaseModel):
    volatility: float
    sharpe: float
    max_drawdown: float
    beta: float
    cumulative_return: float
    top3_concentration: float
    herfindahl: float


class ExposureOut(BaseModel):
    sector: dict[str, float]
    country: dict[str, float]
    currency: dict[str, float]


class HistoryPoint(BaseModel):
    date: str
    portfolio: float
    benchmark: float | None


class CorrelationOut(BaseModel):
    tickers: list[str]
    matrix: list[list[float]]
