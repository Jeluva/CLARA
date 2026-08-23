"""Data freshness per source (see docs/devlog/BACKLOG.md, v2 item 9): when
each source last landed data. Read straight from the bronze layer's
`fetched_at` -- the one timestamp every ingestor already writes on every run,
regardless of each source's own silver schema (some, like `transcripts`,
don't carry an ingestion timestamp of their own).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.storage.models.bronze import BronzeRecord

# Keep in sync with app.api.data_entry._INGESTORS.
SOURCES: dict[str, str] = {
    "prices": "Precios",
    "news": "Noticias",
    "transcripts": "Transcripciones",
    "fundamentals": "Fundamentals",
}


def get_freshness(db: Session) -> list[dict]:
    """For each known source: when it last promoted data (`last_success_at`)
    and when it was last attempted at all (`last_attempt_at`). The two
    differ when the most recent run quarantined everything -- worth
    surfacing given the documented yfinance/YouTube blocking workarounds."""
    last_attempt = dict(
        db.execute(
            select(BronzeRecord.source_table, func.max(BronzeRecord.fetched_at)).group_by(
                BronzeRecord.source_table
            )
        ).all()
    )
    last_success = dict(
        db.execute(
            select(BronzeRecord.source_table, func.max(BronzeRecord.fetched_at))
            .where(BronzeRecord.status == "promoted")
            .group_by(BronzeRecord.source_table)
        ).all()
    )

    return [
        {
            "source": source,
            "label": label,
            "last_success_at": (
                last_success[source].isoformat() if last_success.get(source) else None
            ),
            "last_attempt_at": (
                last_attempt[source].isoformat() if last_attempt.get(source) else None
            ),
        }
        for source, label in SOURCES.items()
    ]
