"""Research endpoints: correlation matrix (indicators land in Phase 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import CorrelationOut
from app.services import portfolio_service as svc
from app.services import research_service
from app.storage.database import get_db

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/correlation", response_model=CorrelationOut)
def correlation(db: Session = Depends(get_db)) -> CorrelationOut:
    """Correlation matrix of daily returns across held assets."""
    return CorrelationOut(**svc.get_correlation(db))


@router.get("/indicators")
def indicators(ticker: str, db: Session = Depends(get_db)) -> dict:
    """Price series with SMA(20), SMA(50) and RSI(14) for one ticker."""
    return research_service.get_indicators(db, ticker)


@router.get("/compare")
def compare(tickers: str, db: Session = Depends(get_db)) -> list[dict]:
    """Compare key metrics across multiple assets. Tickers comma-separated."""
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    return research_service.compare_assets(db, ticker_list)
