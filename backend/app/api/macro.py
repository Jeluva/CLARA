"""Macro endpoints (mock data — see macro_service / README)."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.macro_service import get_macro

router = APIRouter(prefix="/api/macro", tags=["macro"])


@router.get("")
def macro() -> list[dict]:
    """Reference indices, FX and rates as ticker-style cards."""
    return get_macro()
