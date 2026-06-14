"""Data-quality quarantine: records that failed validation, never discarded.

Anything that fails a check on its way from bronze to silver lands here with the
reason, so nothing is lost silently and bad data can be inspected/replayed.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class Quarantine(Base):
    """A rejected record plus the check it failed."""

    __tablename__ = "quarantine"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_table: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload: Mapped[str] = mapped_column(Text)
    failed_check: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
