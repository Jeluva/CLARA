"""Gold layer: aggregated metrics, ready to serve.

A daily snapshot of portfolio-level numbers computed by the analytics layer.
One row per `snapshot_date` (idempotent recompute).
"""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class MetricsDaily(Base):
    """Portfolio-level metrics for a given day."""

    __tablename__ = "metrics_daily"
    __table_args__ = (
        UniqueConstraint("snapshot_date", name="uq_metrics_snapshot_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_date: Mapped[date_type] = mapped_column(index=True)
    portfolio_value: Mapped[float] = mapped_column(Float, default=0.0)
    daily_return: Mapped[float] = mapped_column(Float, default=0.0)
    cumulative_return: Mapped[float] = mapped_column(Float, default=0.0)
    drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
