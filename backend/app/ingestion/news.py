"""Mock news ingestion: realistic English financial headlines per ticker.

Headlines are English (plausible for US-listed names / CEDEARs) so VADER scores
them for real — the sentiment is computed, not hardcoded. Same medallion path as
prices: build payloads -> bronze -> validate -> promote. Idempotent on the URL.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.sentiment import score
from app.quality.promote import PromotionResult, promote_bronze
from app.storage.models.bronze import BronzeRecord

# (ticker, title, summary, source, days_ago)
_HEADLINES: list[tuple[str, str, str, str, int]] = [
    ("AAPL", "Apple shares surge to record high on strong earnings beat",
     "iPhone demand and services revenue topped Wall Street estimates.",
     "MarketWatch", 1),
    ("AAPL", "Analysts raise Apple price targets after blockbuster quarter",
     "Several firms lifted targets citing resilient margins.", "Reuters", 4),
    ("AAPL", "Apple faces antitrust scrutiny over App Store fees",
     "Regulators question commission structure in new probe.", "Bloomberg", 9),
    ("MSFT", "Microsoft cloud growth accelerates, beating expectations",
     "Azure revenue jumped as AI workloads expanded.", "CNBC", 2),
    ("MSFT", "Microsoft announces major AI partnership and new Copilot tier",
     "The deal expands enterprise AI offerings.", "The Verge", 6),
    ("NVDA", "Nvidia smashes revenue records on insatiable AI chip demand",
     "Data-center sales more than doubled year over year.", "Reuters", 1),
    ("NVDA", "Nvidia stock tumbles on fears of cooling AI spending",
     "Investors worry hyperscaler budgets may slow.", "Bloomberg", 5),
    ("KO", "Coca-Cola raises full-year guidance on pricing power",
     "Higher prices offset softer volumes.", "WSJ", 3),
    ("KO", "Coca-Cola dividend hike rewards long-term shareholders",
     "The board approved its 62nd consecutive annual increase.", "Barron's", 8),
    ("GGAL", "Grupo Galicia profits jump as Argentine rates stay high",
     "Net interest income rose sharply in the quarter.", "Ambito", 2),
    ("GGAL", "Argentine banks rally on optimism over economic reforms",
     "Financial stocks led gains amid reform hopes.", "BAE", 7),
    ("YPFD", "YPF boosts Vaca Muerta output to record levels",
     "Shale production drove a strong operational quarter.", "Reuters", 3),
    ("YPFD", "YPF shares slip on lower international crude prices",
     "Falling oil weighed on the energy sector.", "Bloomberg", 6),
    ("AL30", "Argentine bonds rally as country risk falls sharply",
     "Sovereign debt gained on improving fiscal outlook.", "Reuters", 2),
    ("AL30", "Investors cautious on Argentine debt ahead of key vote",
     "Uncertainty kept some buyers on the sidelines.", "Bloomberg", 10),
]


def _today() -> date:
    return datetime.now(timezone.utc).date()


def run_mock_news_ingestion(db: Session) -> PromotionResult:
    """Ingest the mock headline set, scoring sentiment with VADER."""
    today = _today()
    for ticker, title, summary, source, days_ago in _HEADLINES:
        published = today - timedelta(days=days_ago)
        slug = title.lower().replace(" ", "-")[:60]
        url = f"https://mock.news/{ticker.lower()}/{slug}"
        sentiment = score(f"{title}. {summary}")
        dedupe = url
        already = db.execute(
            select(BronzeRecord).where(
                BronzeRecord.source_table == "news",
                BronzeRecord.dedupe_key == dedupe,
            )
        ).scalar_one_or_none()
        if already is not None:
            continue
        db.add(
            BronzeRecord(
                source_table="news",
                source=source,
                dedupe_key=dedupe,
                payload=json.dumps(
                    {
                        "ticker": ticker,
                        "title": title,
                        "summary": summary,
                        "url": url,
                        "source": source,
                        "sentiment": sentiment,
                        "published_at": published.isoformat(),
                    }
                ),
            )
        )
    db.commit()
    return promote_bronze(db)
