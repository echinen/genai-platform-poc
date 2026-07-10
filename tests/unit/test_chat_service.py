import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.chat_service import ChatService


def test_process_calls_llm_persists_and_returns_entity():
    """Garantir fluxo principal: salvar PENDING, chamar LLM e retornar entidade SUCCESS."""

    fake_db = MagicMock()

    service = ChatService()
    service.repository = MagicMock()
    service.llm = MagicMock()
    service.llm.generate = AsyncMock(return_value="Resposta mockada")

    def save_side_effect(_db, entity):
        entity.id = 1
        entity.created_at = datetime.now(timezone.utc)
        return entity

    service.repository.save.side_effect = save_side_effect

    with patch("src.services.chat_service.SessionLocal", return_value=fake_db):
        entity = asyncio.run(service.process("12345", "Pergunta de teste"))

    service.repository.save.assert_called_once()
    service.llm.generate.assert_awaited_once_with("Pergunta de teste")

    assert entity.id == 1
    assert entity.user_id == "12345"
    assert entity.prompt == "Pergunta de teste"
    assert entity.response == "Resposta mockada"
    assert entity.status == "SUCCESS"
    assert isinstance(entity.processing_time_ms, int)

    fake_db.commit.assert_called_once()
    fake_db.refresh.assert_called_once_with(entity)
    fake_db.close.assert_called_once()
