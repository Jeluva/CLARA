"""News & sentiment endpoints."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import NewsItemOut, TickerSentimentOut, TranscriptOut
from app.services import news_service as svc
from app.storage.database import get_db

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/news", response_model=list[NewsItemOut])
def news(
    ticker: str | None = None, db: Session = Depends(get_db)
) -> list[NewsItemOut]:
    """News feed, latest first; optional ?ticker= filter."""
    return [NewsItemOut(**asdict(n)) for n in svc.list_news(db, ticker)]


@router.get("/news/sentiment", response_model=list[TickerSentimentOut])
def news_sentiment(db: Session = Depends(get_db)) -> list[TickerSentimentOut]:
    """Average sentiment per ticker."""
    return [TickerSentimentOut(**asdict(t)) for t in svc.sentiment_by_ticker(db)]


@router.get("/news/sentiment/series")
def sentiment_series(
    ticker: str | None = None, db: Session = Depends(get_db)
) -> list[dict]:
    """Daily average sentiment over time, optionally filtered by ticker."""
    return [asdict(p) for p in svc.sentiment_series(db, ticker)]


@router.get("/transcripts", response_model=list[TranscriptOut])
def transcripts(db: Session = Depends(get_db)) -> list[TranscriptOut]:
    """Summarised YouTube transcripts with sentiment."""
    return [TranscriptOut(**t) for t in svc.list_transcripts(db)]
