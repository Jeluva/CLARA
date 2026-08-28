"""Silver layer: clean, typed, deduplicated business entities.

These are the tables analytics reads from. Natural-key UNIQUE constraints make
ingestion idempotent (re-running a job upserts instead of duplicating).
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.storage.database import Base


class Asset(Base):
    """A tradable instrument. `ticker` is the natural key."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    # asset_class: cedear | equity | etf | bond | fx | crypto
    asset_class: Mapped[str] = mapped_column(String(32))
    sector: Mapped[str] = mapped_column(String(64), default="Unknown")
    country: Mapped[str] = mapped_column(String(64), default="Unknown")
    currency: Mapped[str] = mapped_column(String(8), default="USD")

    positions: Mapped[list[Position]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    prices: Mapped[list[Price]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class Portfolio(Base):
    """A named group of positions. Lets the user keep holdings from
    different brokers/accounts organized separately and switch between them
    in the UI (see docs/devlog/BACKLOG.md, v3 item 1). `portfolio_id=None`
    on the read side means "all portfolios merged" -- there's no separate
    aggregation path, merging positions across portfolios *is* the
    no-filter case."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    positions: Mapped[list[Position]] = relationship(back_populates="portfolio")


class Position(Base):
    """An open or closed holding of an asset, with average cost basis."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_cost: Mapped[float] = mapped_column(Float)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open|closed

    asset: Mapped[Asset] = relationship(back_populates="positions")
    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")


class Transaction(Base):
    """A buy or sell execution. Positions can be derived/reconciled from these."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    type: Mapped[str] = mapped_column(String(8))  # buy|sell
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    executed_at: Mapped[datetime] = mapped_column(DateTime)


class Price(Base):
    """A daily close for an asset. UNIQUE(asset_id, date) for idempotency."""

    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("asset_id", "date", name="uq_price_asset_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    date: Mapped[date_type] = mapped_column(index=True)
    close: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32), default="mock")
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="prices")


class News(Base):
    """A news item tied to an asset, with a sentiment score in [-1, 1]."""

    __tablename__ = "news"
    __table_args__ = (UniqueConstraint("url", name="uq_news_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1024))
    source: Mapped[str] = mapped_column(String(128), default="mock")
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    published_at: Mapped[datetime] = mapped_column(DateTime)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Transcript(Base):
    """A YouTube transcript, summarised, with a sentiment score in [-1, 1]."""

    __tablename__ = "transcripts"
    __table_args__ = (UniqueConstraint("video_id", name="uq_transcript_video"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_channel: Mapped[str] = mapped_column(String(128))
    video_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024))
    transcript: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    published_at: Mapped[datetime] = mapped_column(DateTime)


class Fundamentals(Base):
    """Latest fundamentals snapshot for an asset. One row per asset — this is
    a point-in-time view (current valuation), not a history; re-ingesting
    overwrites it. `asset_id` is the natural key."""

    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("asset_id", name="uq_fundamentals_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)

    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    forward_pe: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_to_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    peg_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_yield: Mapped[float | None] = mapped_column(Float, nullable=True)
    payout_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    earnings_growth: Mapped[float | None] = mapped_column(Float, nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    analyst_target_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    analyst_recommendation: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    next_earnings_date: Mapped[date_type | None] = mapped_column(nullable=True)

    # Bond-only fields (docs/devlog/BACKLOG.md v4 item 1) -- null for
    # equities/ETFs the same way pe_ratio etc. are null for bonds. Sourced
    # from bonistas.com, the only free no-login source found with TIR/
    # duration for AR sovereigns (see docs/BLOCKED.md history).
    bond_tir: Mapped[float | None] = mapped_column(Float, nullable=True)
    bond_tem: Mapped[float | None] = mapped_column(Float, nullable=True)
    bond_tna: Mapped[float | None] = mapped_column(Float, nullable=True)
    bond_modified_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    bond_parity: Mapped[float | None] = mapped_column(Float, nullable=True)
    bond_days_to_coupon: Mapped[int | None] = mapped_column(nullable=True)

    source: Mapped[str] = mapped_column(String(32), default="mock")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped[Asset] = relationship()


class Thesis(Base):
    """A journal entry: why an asset was bought, price target and stop-loss,
    conviction — kept alongside the position so the real outcome can be
    contrasted against the original reasoning later (see
    docs/devlog/BACKLOG.md, v2 item 6)."""

    __tablename__ = "theses"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    note: Mapped[str] = mapped_column(Text)
    price_at_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    # conviction: baja | media | alta
    conviction: Mapped[str] = mapped_column(String(16), default="media")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped[Asset] = relationship()


class Alert(Base):
    """A watch rule: metric + condition + threshold, evaluated live on every
    read instead of via a background job -- no notification channel exists
    yet, so "triggered" just means the condition currently holds (see
    docs/devlog/BACKLOG.md, v2 item 8)."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    # metric: price | sentiment | pe_ratio
    metric: Mapped[str] = mapped_column(String(16))
    # condition: above | below
    condition: Mapped[str] = mapped_column(String(8))
    threshold: Mapped[float] = mapped_column(Float)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    asset: Mapped[Asset] = relationship()


class YoutubeChannel(Base):
    """A YouTube channel followed for transcript ingestion. `channel_id` is
    the natural key (canonical YouTube channel ID, resolved from the handle
    the user typed in)."""

    __tablename__ = "youtube_channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    handle: Mapped[str] = mapped_column(String(128), default="")
    display_name: Mapped[str] = mapped_column(String(256), default="")
    active: Mapped[bool] = mapped_column(default=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
