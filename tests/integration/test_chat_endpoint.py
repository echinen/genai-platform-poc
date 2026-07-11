from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch


def test_chat_endpoint_returns_200_and_expected_payload(app_client):
    """Validar contrato do endpoint /v1/chat sem chamar Gemini ou PostgreSQL reais."""

    fake_entity = type("PromptEntity", (), {})()
    fake_entity.id = 42
    fake_entity.user_id = "12345"
    fake_entity.prompt = "Como esta a cotacao do dolar hoje?"
    fake_entity.response = "A cotacao do dolar hoje e R$5,10."
    fake_entity.model = "gemini-3.5-flash"
    fake_entity.created_at = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)

    with patch("src.api.chat_controller.service.process", AsyncMock(return_value=fake_entity)):
        response = app_client.post(
            "/v1/chat",
            json={"userId": "12345", "prompt": "Como esta a cotacao do dolar hoje?"},
            headers={"X-API-Key": "test-api-key"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": 42,
        "userId": "12345",
        "prompt": "Como esta a cotacao do dolar hoje?",
        "response": "A cotacao do dolar hoje e R$5,10.",
        "model": "gemini-3.5-flash",
        "timestamp": "2026-07-10T12:00:00Z",
    }


def test_chat_endpoint_returns_401_without_api_key(app_client):
    """Validar protecao do endpoint quando API key nao e enviada."""

    response = app_client.post(
        "/v1/chat",
        json={"userId": "12345", "prompt": "Como esta a cotacao do dolar hoje?"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
