"""All ORM models, re-exported so `Base.metadata` sees every table.

Import order doesn't matter for table creation, but importing everything here
guarantees Alembic autogenerate and create_all pick up the full schema.
"""

from app.storage.models.bronze import BronzeRecord
from app.storage.models.gold import MetricsDaily
from app.storage.models.quality import Quarantine
from app.storage.models.silver import (
    Asset,
    News,
    Position,
    Price,
    Transaction,
    Transcript,
)

__all__ = [
    "Asset",
    "Position",
    "Transaction",
    "Price",
    "News",
    "Transcript",
    "MetricsDaily",
    "BronzeRecord",
    "Quarantine",
]
