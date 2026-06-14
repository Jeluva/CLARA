"""Pydantic response models for the API. Keep serialization explicit and typed."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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


# --- Data-entry request models -----------------------------------------------


class AssetCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    asset_class: str = Field(min_length=1, max_length=32)
    sector: str = "Unknown"
    country: str = "Unknown"
    currency: str = Field(default="USD", min_length=1, max_length=8)


class AssetOut(BaseModel):
    id: int
    ticker: str
    name: str
    asset_class: str
    sector: str
    country: str
    currency: str


class PositionCreate(BaseModel):
    ticker: str = Field(min_length=1)
    quantity: float = Field(gt=0)
    avg_cost: float = Field(gt=0)
    opened_at: datetime | None = None


class PositionOutFull(BaseModel):
    id: int
    ticker: str
    quantity: float
    avg_cost: float
    opened_at: datetime
    status: str


class TransactionCreate(BaseModel):
    ticker: str = Field(min_length=1)
    type: str = Field(pattern="^(buy|sell)$")
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    fee: float = Field(default=0.0, ge=0)
    executed_at: datetime | None = None


class IngestionResult(BaseModel):
    source: str
    promoted: int
    quarantined: int
    message: str


# --- News & sentiment --------------------------------------------------------


class NewsItemOut(BaseModel):
    id: int
    ticker: str | None
    title: str
    summary: str
    url: str
    source: str
    sentiment: float
    sentiment_label: str
    published_at: str


class TickerSentimentOut(BaseModel):
    ticker: str
    score: float
    label: str
    count: int


class TranscriptOut(BaseModel):
    id: int
    source_channel: str
    title: str
    url: str
    summary: str
    sentiment: float
    sentiment_label: str
    published_at: str
