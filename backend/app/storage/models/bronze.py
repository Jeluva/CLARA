"""Bronze layer: raw payloads exactly as the source returned them.

A single generic table stores raw records from every source so we can reprocess
into silver without re-calling the network. `status` tracks the medallion flow:
pending -> promoted | quarantined.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class BronzeRecord(Base):
    """A raw payload from a source, awaiting validation/promotion."""

    __tablename__ = "bronze_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The silver table this record is destined for, e.g. "prices", "news".
    source_table: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64), default="mock")
    # Natural key of the record, used to dedupe bronze ingestion itself.
    dedupe_key: Mapped[str] = mapped_column(String(256), index=True)
    payload: Mapped[str] = mapped_column(Text)  # raw JSON string
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
