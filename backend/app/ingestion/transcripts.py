"""Mock YouTube transcript ingestion: analyst videos with summary + sentiment.

Stands in for `youtube-transcript-api` during dev (no network). Each fixture
carries a short English summary VADER scores for real. Idempotent on video_id.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.sentiment import score
from app.quality.promote import PromotionResult, promote_bronze
from app.storage.models.bronze import BronzeRecord

# (video_id, channel, title, summary, days_ago)
_VIDEOS: list[tuple[str, str, str, str, int]] = [
    ("vid_tech01", "Mercado en Foco",
     "Tech earnings recap: why Apple and Microsoft still look strong",
     "The analyst is bullish: strong cash flow, expanding margins and durable "
     "demand make these high-quality compounders worth holding.", 2),
    ("vid_nvda02", "Wall Street AR",
     "Is the AI trade overheating? A look at Nvidia's valuation",
     "Mixed view: the growth is real and impressive, but the rich valuation "
     "leaves little room for disappointment if demand slows.", 4),
    ("vid_arg03", "Inversor Global",
     "Argentine assets: opportunity or value trap?",
     "Cautiously optimistic: reforms could unlock big upside in banks and "
     "energy, though political risk remains a serious concern.", 3),
    ("vid_bonds04", "Renta Fija Hoy",
     "Sovereign bonds rally: how much further can AL30 run?",
     "Positive tone: falling country risk and improving fiscal numbers support "
     "further gains, but the analyst warns against chasing the move.", 5),
]


def _today() -> date:
    return datetime.now(timezone.utc).date()


def run_mock_transcript_ingestion(db: Session) -> PromotionResult:
    today = _today()
    for video_id, channel, title, summary, days_ago in _VIDEOS:
        published = today - timedelta(days=days_ago)
        already = db.execute(
            select(BronzeRecord).where(
                BronzeRecord.source_table == "transcripts",
                BronzeRecord.dedupe_key == video_id,
            )
        ).scalar_one_or_none()
        if already is not None:
            continue
        db.add(
            BronzeRecord(
                source_table="transcripts",
                source=channel,
                dedupe_key=video_id,
                payload=json.dumps(
                    {
                        "video_id": video_id,
                        "source_channel": channel,
                        "title": title,
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "transcript": summary,  # mock: summary stands in for full text
                        "summary": summary,
                        "sentiment": score(summary),
                        "published_at": published.isoformat(),
                    }
                ),
            )
        )
    db.commit()
    return promote_bronze(db)
