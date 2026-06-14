"""Research endpoints: correlation matrix (indicators land in Phase 7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import CorrelationOut
from app.services import portfolio_service as svc
from app.storage.database import get_db

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/correlation", response_model=CorrelationOut)
def correlation(db: Session = Depends(get_db)) -> CorrelationOut:
    """Correlation matrix of daily returns across held assets."""
    return CorrelationOut(**svc.get_correlation(db))
