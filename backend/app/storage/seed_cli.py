"""CLI to seed the dev database. Run: `python -m app.storage.seed_cli`.

Assumes the schema exists (`alembic upgrade head`). Idempotent — safe to re-run.
"""

from __future__ import annotations

from app.storage.database import SessionLocal
from app.storage.seed import seed_database


def main() -> None:
    with SessionLocal() as db:
        counts = seed_database(db)
    print("Seed complete:")
    for key, value in counts.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
