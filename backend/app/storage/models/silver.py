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


class Position(Base):
    """An open or closed holding of an asset, with average cost basis."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_cost: Mapped[float] = mapped_column(Float)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16), default="open")  # open|closed

    asset: Mapped[Asset] = relationship(back_populates="positions")


class Transaction(Base):
    """A buy or sell execution. Positions can be derived/reconciled from these."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
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
