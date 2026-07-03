"""YouTube transcript ingestion: real scraping of followed channels, with a
deterministic mock fallback for dev/tests.

Real mode: for each active `YoutubeChannel`, lists its latest uploads via
`yt-dlp` (no API key) and fetches each new video's transcript via
`youtube-transcript-api`. Idempotent on video_id — already-seen videos are
skipped without a network call.

Mock mode: static fixture videos, VADER-scored for real. Used when no channel
is followed, or when USE_MOCK_SOURCES=true.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion import youtube
from app.ingestion.sentiment import score
from app.quality.promote import PromotionResult, promote_bronze
from app.storage.models.bronze import BronzeRecord
from app.storage.models.silver import YoutubeChannel

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


# ---------------------------------------------------------------------------
# Real ingestion: followed channels
# ---------------------------------------------------------------------------

_VIDEOS_PER_CHANNEL = 5


def _parse_upload_date(raw: str | None) -> str:
    if not raw:
        return _today().isoformat()
    try:
        return datetime.strptime(raw, "%Y%m%d").date().isoformat()
    except ValueError:
        return _today().isoformat()


def run_channel_transcript_ingestion(db: Session) -> PromotionResult:
    channels = db.execute(
        select(YoutubeChannel).where(YoutubeChannel.active.is_(True))
    ).scalars().all()

    for channel in channels:
        videos = youtube.list_latest_videos(channel.channel_id, limit=_VIDEOS_PER_CHANNEL)
        for video in videos:
            video_id = video["video_id"]
            already = db.execute(
                select(BronzeRecord).where(
                    BronzeRecord.source_table == "transcripts",
                    BronzeRecord.dedupe_key == video_id,
                )
            ).first()
            if already is not None:
                continue

            transcript = youtube.fetch_transcript(video_id)
            if not transcript:
                continue  # captions disabled/unavailable — nothing to ingest

            summary = transcript[:400] + ("…" if len(transcript) > 400 else "")
            db.add(
                BronzeRecord(
                    source_table="transcripts",
                    source=channel.display_name or channel.handle,
                    dedupe_key=video_id,
                    payload=json.dumps(
                        {
                            "video_id": video_id,
                            "source_channel": channel.display_name or channel.handle,
                            "title": video["title"],
                            "url": f"https://youtube.com/watch?v={video_id}",
                            "transcript": transcript,
                            "summary": summary,
                            "sentiment": score(transcript),
                            "published_at": _parse_upload_date(video.get("upload_date")),
                        }
                    ),
                )
            )
    db.commit()
    return promote_bronze(db)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_transcript_ingestion(db: Session) -> PromotionResult:
    """Real ingestion from followed channels; mock if none are followed."""
    from app.config import settings

    if settings.use_mock_sources:
        return run_mock_transcript_ingestion(db)

    has_channels = db.execute(
        select(YoutubeChannel.id).where(YoutubeChannel.active.is_(True)).limit(1)
    ).first()
    if has_channels:
        return run_channel_transcript_ingestion(db)
    return run_mock_transcript_ingestion(db)
