"""Portfolio endpoints: overview, risk metrics, exposure, value history."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.schemas import (
    ExposureOut,
    HistoryPoint,
    PortfolioOverviewOut,
    PositionSizeOut,
    RiskMetricsOut,
    SimulationOut,
    SimulationRequest,
)
from app.services import portfolio_service as svc
from app.storage.database import get_db

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioOverviewOut)
def portfolio_overview(
    portfolio_id: int | None = None, db: Session = Depends(get_db)
) -> PortfolioOverviewOut:
    """Total value, P&L (total and daily), and the position table.
    `portfolio_id` omitted merges every portfolio."""
    overview = svc.get_portfolio_overview(db, portfolio_id)
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
def risk_metrics(
    portfolio_id: int | None = None, db: Session = Depends(get_db)
) -> RiskMetricsOut:
    """Volatility, Sharpe, max drawdown, beta, concentration."""
    return RiskMetricsOut(**asdict(svc.get_risk_metrics(db, portfolio_id)))


@router.get("/exposure", response_model=ExposureOut)
def exposure(
    portfolio_id: int | None = None, db: Session = Depends(get_db)
) -> ExposureOut:
    """Exposure weights by sector, country and currency."""
    return ExposureOut(**svc.get_exposure(db, portfolio_id))


@router.get("/history", response_model=list[HistoryPoint])
def history(
    portfolio_id: int | None = None, db: Session = Depends(get_db)
) -> list[HistoryPoint]:
    """Cumulative-return series of the portfolio vs the benchmark."""
    return [HistoryPoint(**point) for point in svc.get_history(db, portfolio_id)]


@router.get("/realized-history")
def realized_history(
    portfolio_id: int | None = None, db: Session = Depends(get_db)
) -> list[dict]:
    """P&L realizado respetando opened_at de cada posición (ADR 0003 V2)."""
    return svc.get_realized_history(db, portfolio_id)


@router.post("/simulate", response_model=SimulationOut)
def simulate(body: SimulationRequest, db: Session = Depends(get_db)) -> SimulationOut:
    """"Qué pasa si compro esto": impacto de una compra hipotética en
    concentración, exposición y correlación, sin tocar ninguna posición."""
    try:
        result = svc.simulate_purchase(
            db, body.ticker, body.amount, body.portfolio_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SimulationOut(**asdict(result))


@router.get("/position-size/{ticker}", response_model=PositionSizeOut)
def position_size(
    ticker: str,
    risk_budget_pct: float = Query(default=svc.DEFAULT_RISK_BUDGET_PCT, gt=0, le=1),
    portfolio_id: int | None = None,
    db: Session = Depends(get_db),
) -> PositionSizeOut:
    """Guía de tamaño de posición: cuánto sugiere tener en este activo un
    presupuesto de riesgo escalado por su volatilidad anualizada."""
    try:
        result = svc.get_position_size_guide(db, ticker, risk_budget_pct, portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PositionSizeOut(**asdict(result))
