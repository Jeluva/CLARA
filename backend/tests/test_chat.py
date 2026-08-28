"""Tests for the chatbot service (no API key needed — fallback path)."""

from __future__ import annotations

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.services import chat_service
from app.services.asset_service import get_asset_summary
from app.services.chat_service import ChatMessage
from app.storage.seed import seed_database


def test_chat_without_key_returns_fallback_with_context(db: Session) -> None:
    seed_database(db)
    with patch.object(chat_service, "settings") as mock_settings:
        mock_settings.groq_api_key = ""
        mock_settings.qwen_api_key = ""
        mock_settings.gemini_api_key = ""
        mock_settings.anthropic_api_key = ""
        mock_settings.ollama_enabled = False
        result = chat_service.fundamental_analysis(
            db, "AAPL", [ChatMessage(role="user", content="¿Qué es Apple?")]
        )
    assert result["configured"] is False
    assert "AAPL" in result["reply"]
    assert "Apple" in result["reply"]


def test_reply_ollama_returns_none_on_any_exception() -> None:
    """Any failure (server down, model not registered, timeout) falls
    through to static rather than surfacing an error -- Ollama is the last
    LLM fallback, not a provider whose errors are worth showing the user
    (docs/devlog/BACKLOG.md, v5 item 3)."""
    with patch("openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.side_effect = RuntimeError("boom")
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.ollama_model = "clara-local"
            mock_settings.chat_model = ""
            result = chat_service._reply_ollama(
                "context", [ChatMessage(role="user", content="hola")]
            )
    assert result is None


def test_reply_ollama_strips_closed_think_block() -> None:
    fake_message = type(
        "M", (), {"content": "<think>razonando en voz alta...</think>\n\nLa respuesta real."}
    )()
    fake_choice = type("C", (), {"message": fake_message})()
    fake_response = type("R", (), {"choices": [fake_choice]})()

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = fake_response
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.ollama_model = "clara-local"
            mock_settings.chat_model = ""
            result = chat_service._reply_ollama(
                "context", [ChatMessage(role="user", content="hola")]
            )
    assert result == {"reply": "La respuesta real.", "configured": True}


def test_reply_ollama_returns_none_when_thinking_never_closes() -> None:
    """The model ran out of its token budget still inside <think> (seen
    live: 150 tokens of reasoning, finish_reason="length", zero real
    answer) -- an empty reply after stripping should fall through to
    static, not return a blank chat bubble."""
    fake_message = type(
        "M", (), {"content": "\n\n<think>\nThinking Process:\n1. Analyze..."}
    )()
    fake_choice = type("C", (), {"message": fake_message})()
    fake_response = type("R", (), {"choices": [fake_choice]})()

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = fake_response
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.ollama_model = "clara-local"
            mock_settings.chat_model = ""
            result = chat_service._reply_ollama(
                "context", [ChatMessage(role="user", content="hola")]
            )
    assert result is None


def test_reply_ollama_keeps_answer_that_precedes_an_unclosed_think_block() -> None:
    """Observed live: the model sometimes emits the answer *before* an
    unclosed <think> block instead of after a closed one -- whatever
    precedes "<think>" should still count as a usable answer."""
    fake_message = type("M", (), {"content": "4\n\n<think>\nDouble-checking..."})()
    fake_choice = type("C", (), {"message": fake_message})()
    fake_response = type("R", (), {"choices": [fake_choice]})()

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = fake_response
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.ollama_model = "clara-local"
            mock_settings.chat_model = ""
            result = chat_service._reply_ollama(
                "context", [ChatMessage(role="user", content="hola")]
            )
    assert result == {"reply": "4", "configured": True}


def test_reply_ollama_strips_leading_directive_echo() -> None:
    """Verified live: the model sometimes echoes "/no_think" (or a garbled
    variant of it) as the first line of its reply instead of following it
    silently."""
    fake_message = type(
        "M", (), {"content": "/stop\n\nAquí tienes el análisis solicitado."}
    )()
    fake_choice = type("C", (), {"message": fake_message})()
    fake_response = type("R", (), {"choices": [fake_choice]})()

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = fake_response
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.ollama_model = "clara-local"
            mock_settings.chat_model = ""
            result = chat_service._reply_ollama(
                "context", [ChatMessage(role="user", content="hola")]
            )
    assert result == {"reply": "Aquí tienes el análisis solicitado.", "configured": True}


def test_reply_ollama_appends_no_think_to_last_message() -> None:
    with patch("openai.OpenAI") as mock_openai_cls:
        mock_create = mock_openai_cls.return_value.chat.completions.create
        mock_create.return_value = type(
            "R", (), {"choices": [type("C", (), {"message": type("M", (), {"content": "ok"})()})()]}
        )()
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.ollama_model = "clara-local"
            mock_settings.chat_model = ""
            chat_service._reply_ollama(
                "context", [ChatMessage(role="user", content="¿qué opinás de AAPL?")]
            )
    sent_messages = mock_create.call_args.kwargs["messages"]
    assert sent_messages[-1]["content"] == "¿qué opinás de AAPL?\n/no_think"


def test_reply_ollama_returns_reply_on_success() -> None:
    fake_message = type("M", (), {"content": "  respuesta del modelo local  "})()
    fake_choice = type("C", (), {"message": fake_message})()
    fake_response = type("R", (), {"choices": [fake_choice]})()

    with patch("openai.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value = fake_response
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434/v1"
            mock_settings.ollama_model = "clara-local"
            mock_settings.chat_model = ""
            result = chat_service._reply_ollama(
                "context", [ChatMessage(role="user", content="hola")]
            )
    assert result == {"reply": "respuesta del modelo local", "configured": True}


def test_chat_falls_through_to_ollama_when_cloud_providers_unavailable(
    db: Session,
) -> None:
    seed_database(db)
    with patch.object(chat_service, "_reply_ollama") as mock_ollama:
        mock_ollama.return_value = {"reply": "respuesta local", "configured": True}
        with patch.object(chat_service, "settings") as mock_settings:
            mock_settings.groq_api_key = ""
            mock_settings.qwen_api_key = ""
            mock_settings.gemini_api_key = ""
            mock_settings.anthropic_api_key = ""
            mock_settings.ollama_enabled = True
            result = chat_service.fundamental_analysis(
                db, "AAPL", [ChatMessage(role="user", content="hola")]
            )
    assert result == {"reply": "respuesta local", "configured": True}
    mock_ollama.assert_called_once()


def test_asset_summary_shape(db: Session) -> None:
    seed_database(db)
    summary = get_asset_summary(db, "AAPL")
    assert summary is not None
    assert summary["ticker"] == "AAPL"
    assert summary["position"] is not None  # AAPL is held in the seed
    assert summary["latest_price"] is not None
    assert summary["news_count"] >= 0


def test_asset_summary_missing(db: Session) -> None:
    seed_database(db)
    assert get_asset_summary(db, "ZZZZ") is None
