"""Bronze → silver promotion engine.

Walks pending bronze records, validates each against its table's checks, and
either upserts it into the silver layer (idempotent on the natural key) or moves
it to quarantine with the failure reason. Running it twice is safe: already
promoted/quarantined records are skipped and upserts don't duplicate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.quality.checks import run_checks
from app.storage.models.bronze import BronzeRecord
from app.storage.models.quality import Quarantine
from app.storage.models.silver import Asset, News, Price, Transcript


@dataclass
class PromotionResult:
    promoted: int = 0
    quarantined: int = 0
    skipped: int = 0


def _build_context(db: Session) -> dict[str, Any]:
    """Context shared by checks: ticker -> asset_id."""
    rows = db.execute(select(Asset.ticker, Asset.id)).all()
    return {"known_tickers": {ticker: asset_id for ticker, asset_id in rows}}


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.fromisoformat(str(value)).date()


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(
        tzinfo=None
    )


def _upsert_price(db: Session, payload: dict[str, Any], ctx: dict[str, Any]) -> None:
    asset_id = ctx["known_tickers"][payload["ticker"]]
    d = _parse_date(payload["date"])
    existing = db.execute(
        select(Price).where(Price.asset_id == asset_id, Price.date == d)
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            Price(
                asset_id=asset_id,
                date=d,
                close=float(payload["close"]),
                source=payload.get("source", "mock"),
            )
        )
    else:
        existing.close = float(payload["close"])
        existing.source = payload.get("source", existing.source)


def _upsert_news(db: Session, payload: dict[str, Any], ctx: dict[str, Any]) -> None:
    url = payload["url"]
    existing = db.execute(
        select(News).where(News.url == url)
    ).scalar_one_or_none()
    asset_id = ctx["known_tickers"].get(payload.get("ticker"))
    fields = dict(
        asset_id=asset_id,
        title=payload["title"],
        summary=payload.get("summary", ""),
        source=payload.get("source", "mock"),
        sentiment=float(payload.get("sentiment", 0.0) or 0.0),
        published_at=_parse_datetime(payload["published_at"]),
    )
    if existing is None:
        db.add(News(url=url, **fields))
    else:
        for key, value in fields.items():
            setattr(existing, key, value)


def _upsert_transcript(
    db: Session, payload: dict[str, Any], _ctx: dict[str, Any]
) -> None:
    video_id = payload["video_id"]
    existing = db.execute(
        select(Transcript).where(Transcript.video_id == video_id)
    ).scalar_one_or_none()
    fields = dict(
        source_channel=payload.get("source_channel", "unknown"),
        title=payload["title"],
        url=payload.get("url", ""),
        transcript=payload.get("transcript", ""),
        summary=payload.get("summary", ""),
        sentiment=float(payload.get("sentiment", 0.0) or 0.0),
        published_at=_parse_datetime(
            payload.get("published_at")
            or datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        ),
    )
    if existing is None:
        db.add(Transcript(video_id=video_id, **fields))
    else:
        for key, value in fields.items():
            setattr(existing, key, value)


_UPSERTERS = {
    "prices": _upsert_price,
    "news": _upsert_news,
    "transcripts": _upsert_transcript,
}


def promote_bronze(db: Session) -> PromotionResult:
    """Promote all pending bronze records into silver. Idempotent."""
    result = PromotionResult()
    context = _build_context(db)

    pending = (
        db.execute(
            select(BronzeRecord).where(BronzeRecord.status == "pending")
        )
        .scalars()
        .all()
    )

    for record in pending:
        try:
            payload = json.loads(record.payload)
        except json.JSONDecodeError as exc:
            _quarantine(db, record, f"invalid JSON payload: {exc}")
            result.quarantined += 1
            continue

        reason = run_checks(record.source_table, payload, context)
        if reason is not None:
            _quarantine(db, record, reason)
            result.quarantined += 1
            continue

        upserter = _UPSERTERS.get(record.source_table)
        if upserter is None:
            _quarantine(
                db, record, f"no upserter for table '{record.source_table}'"
            )
            result.quarantined += 1
            continue

        upserter(db, payload, context)
        record.status = "promoted"
        result.promoted += 1

    db.commit()
    return result


def _quarantine(db: Session, record: BronzeRecord, reason: str) -> None:
    db.add(
        Quarantine(
            source_table=record.source_table,
            raw_payload=record.payload,
            failed_check=reason,
        )
    )
    record.status = "quarantined"
