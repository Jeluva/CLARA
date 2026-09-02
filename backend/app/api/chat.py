"""Chatbot endpoint: fundamental analysis of an asset, backed by Claude."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import ChatRequest, ChatResponse, PortfolioChatRequest
from app.services import chat_service
from app.services.chat_service import ChatMessage
from app.storage.database import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/fundamental", response_model=ChatResponse)
def fundamental(body: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Answer a question about an asset's fundamentals, grounded in its data."""
    messages = [ChatMessage(role=m.role, content=m.content) for m in body.messages]
    result = chat_service.fundamental_analysis(db, body.ticker, messages)
    return ChatResponse(**result)


@router.post("/portfolio", response_model=ChatResponse)
def portfolio(body: PortfolioChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """Answer a question about the whole portfolio, grounded in a bounded,
    question-aware slice of its data (see chat_service._build_portfolio_context)."""
    messages = [ChatMessage(role=m.role, content=m.content) for m in body.messages]
    result = chat_service.portfolio_analysis(db, messages, body.portfolio_id)
    return ChatResponse(**result)
