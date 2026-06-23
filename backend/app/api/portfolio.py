"""Portfolio endpoints: overview, risk metrics, exposure, value history."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import (
    ExposureOut,
    HistoryPoint,
    PortfolioOverviewOut,
    RiskMetricsOut,
)
from app.services import portfolio_service as svc
from app.storage.database import get_db

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioOverviewOut)
def portfolio_overview(db: Session = Depends(get_db)) -> PortfolioOverviewOut:
    """Total value, P&L (total and daily), and the position table."""
    overview = svc.get_portfolio_overview(db)
    return PortfolioOverviewOut(
        total_value=overview.total_value,
        total_cost=overview.total_cost,
        total_pnl=overview.total_pnl,
        total_pnl_pct=overview.total_pnl_pct,
        daily_pnl=overview.daily_pnl,
        daily_pnl_pct=overview.daily_pnl_pct,
        positions=[asdict(p) for p in overview.positions],  # type: ignore[misc]
    )


@router.get("/metrics", response_model=RiskMetricsOut)
def risk_metrics(db: Session = Depends(get_db)) -> RiskMetricsOut:
    """Volatility, Sharpe, max drawdown, beta, concentration."""
    return RiskMetricsOut(**asdict(svc.get_risk_metrics(db)))


@router.get("/exposure", response_model=ExposureOut)
def exposure(db: Session = Depends(get_db)) -> ExposureOut:
    """Exposure weights by sector, country and currency."""
    return ExposureOut(**svc.get_exposure(db))


@router.get("/history", response_model=list[HistoryPoint])
def history(db: Session = Depends(get_db)) -> list[HistoryPoint]:
    """Cumulative-return series of the portfolio vs the benchmark."""
    return [HistoryPoint(**point) for point in svc.get_history(db)]


@router.get("/realized-history")
def realized_history(db: Session = Depends(get_db)) -> list[dict]:
    """P&L realizado respetando opened_at de cada posición (ADR 0003 V2)."""
    return svc.get_realized_history(db)
