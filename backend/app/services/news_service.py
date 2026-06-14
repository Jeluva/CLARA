"""News & sentiment service: feed with optional ticker filter, aggregate scores."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.sentiment import label
from app.storage.models.silver import Asset, News, Transcript


@dataclass
class NewsItem:
    id: int
    ticker: str | None
    title: str
    summary: str
    url: str
    source: str
    sentiment: float
    sentiment_label: str
    published_at: str


@dataclass
class TickerSentiment:
    ticker: str
    score: float
    label: str
    count: int


def list_news(db: Session, ticker: str | None = None) -> list[NewsItem]:
    """Latest news first, optionally filtered to a single ticker."""
    query = (
        select(News, Asset.ticker)
        .outerjoin(Asset, Asset.id == News.asset_id)
        .order_by(News.published_at.desc())
    )
    if ticker:
        query = query.where(Asset.ticker == ticker.upper())
    rows = db.execute(query).all()
    return [
        NewsItem(
            id=n.id,
            ticker=tk,
            title=n.title,
            summary=n.summary,
            url=n.url,
            source=n.source,
            sentiment=n.sentiment,
            sentiment_label=label(n.sentiment),
            published_at=n.published_at.date().isoformat(),
        )
        for n, tk in rows
    ]


def sentiment_by_ticker(db: Session) -> list[TickerSentiment]:
    """Average sentiment per ticker across its news, most positive first."""
    rows = db.execute(
        select(Asset.ticker, News.sentiment).join(
            News, News.asset_id == Asset.id
        )
    ).all()
    agg: dict[str, list[float]] = {}
    for tk, sentiment in rows:
        agg.setdefault(tk, []).append(sentiment)

    result = [
        TickerSentiment(
            ticker=tk,
            score=round(sum(vals) / len(vals), 4),
            label=label(sum(vals) / len(vals)),
            count=len(vals),
        )
        for tk, vals in agg.items()
    ]
    result.sort(key=lambda t: t.score, reverse=True)
    return result


def list_transcripts(db: Session) -> list[dict]:
    rows = (
        db.execute(select(Transcript).order_by(Transcript.published_at.desc()))
        .scalars()
        .all()
    )
    return [
        {
            "id": t.id,
            "source_channel": t.source_channel,
            "title": t.title,
            "url": t.url,
            "summary": t.summary,
            "sentiment": t.sentiment,
            "sentiment_label": label(t.sentiment),
            "published_at": t.published_at.date().isoformat(),
        }
        for t in rows
    ]
