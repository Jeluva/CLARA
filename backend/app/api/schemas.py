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


class SimulationRequest(BaseModel):
    ticker: str = Field(min_length=1)
    amount: float = Field(gt=0)


class SimulationOut(BaseModel):
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


class PositionSizeOut(BaseModel):
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


class FundamentalsOut(BaseModel):
    ticker: str
    source: str
    updated_at: str | None
    market_cap: float | None
    pe_ratio: float | None
    forward_pe: float | None
    pb_ratio: float | None
    ev_to_ebitda: float | None
    peg_ratio: float | None
    dividend_yield: float | None
    payout_ratio: float | None
    revenue_growth: float | None
    earnings_growth: float | None
    gross_margin: float | None
    operating_margin: float | None
    profit_margin: float | None
    roe: float | None
    debt_to_equity: float | None
    analyst_target_mean: float | None
    analyst_recommendation: str | None
    next_earnings_date: str | None


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


class ThesisCreate(BaseModel):
    ticker: str = Field(min_length=1)
    note: str = Field(min_length=1)
    target_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    conviction: str = Field(default="media", pattern="^(baja|media|alta)$")


class ThesisOut(BaseModel):
    id: int
    ticker: str
    note: str
    price_at_entry: float | None
    target_price: float | None
    stop_loss: float | None
    conviction: str
    created_at: str
    current_price: float | None
    return_since_entry: float | None
    status: str


class IngestionResult(BaseModel):
    source: str
    promoted: int
    quarantined: int
    message: str


class ChannelCreate(BaseModel):
    url_or_handle: str = Field(min_length=1, max_length=256)


class TranscriptIngestItem(BaseModel):
    video_id: str = Field(min_length=1, max_length=32)
    channel: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    transcript: str = Field(min_length=1)
    published_at: str


class ChannelOut(BaseModel):
    id: int
    channel_id: str
    handle: str
    display_name: str
    active: bool
    added_at: datetime


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


# --- Chatbot ------------------------------------------------------------------


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    ticker: str = Field(min_length=1)
    messages: list[ChatTurn] = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    configured: bool
    error: bool = False
