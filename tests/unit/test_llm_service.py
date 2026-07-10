import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.llm_service import LLMService, NonRetryableLLMError


def _mock_async_client(response_or_exc):
    client = MagicMock()
    if isinstance(response_or_exc, Exception):
        client.post = AsyncMock(side_effect=response_or_exc)
    else:
        client.post = AsyncMock(return_value=response_or_exc)

    cm = MagicMock()
    cm.__aenter__.return_value = client
    cm.__aexit__.return_value = False
    return cm


def test_generate_success_with_mocked_http_call():
    """Validar resposta de sucesso sem chamada real externa."""

    service = LLMService()

    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"output": "Texto da LLM"}

    async_client_cm = _mock_async_client(response)

    with patch("src.services.llm_service.httpx.AsyncClient", return_value=async_client_cm), patch(
        "src.services.llm_service.settings.gemini_api_key", "fake-key"
    ), patch("src.services.llm_service.settings.gemini_url", "https://fake-gemini"), patch(
        "src.services.llm_service.settings.gemini_model", "fake-model"
    ):
        result = asyncio.run(service._generate_gemini_with_retry.__wrapped__(service, "Prompt"))

    assert result == "Texto da LLM"


def test_generate_timeout_raises_timeout_error():
    """Validar timeout sem chamar rede real."""

    service = LLMService()
    timeout_exc = httpx.ReadTimeout("timeout", request=httpx.Request("POST", "https://fake-gemini"))

    async_client_cm = _mock_async_client(timeout_exc)

    with patch("src.services.llm_service.httpx.AsyncClient", return_value=async_client_cm), patch(
        "src.services.llm_service.settings.gemini_api_key", "fake-key"
    ), patch("src.services.llm_service.settings.gemini_url", "https://fake-gemini"), patch(
        "src.services.llm_service.settings.gemini_model", "fake-model"
    ):
        with pytest.raises(httpx.ReadTimeout):
            asyncio.run(service._generate_gemini_with_retry.__wrapped__(service, "Prompt"))


def test_generate_external_api_error_raises_http_status_error():
    """Validar erro de API externa sem chamada real: status 400 segue caminho nao-retryable."""

    service = LLMService()

    request = httpx.Request("POST", "https://fake-gemini")
    response = httpx.Response(400, request=request)
    api_error = httpx.HTTPStatusError("bad request", request=request, response=response)

    async_client_cm = _mock_async_client(api_error)

    with patch("src.services.llm_service.httpx.AsyncClient", return_value=async_client_cm), patch(
        "src.services.llm_service.settings.gemini_api_key", "fake-key"
    ), patch(
        "src.services.llm_service.settings.gemini_url", "https://fake-gemini"
    ), patch("src.services.llm_service.settings.gemini_model", "fake-model"):
        with pytest.raises(NonRetryableLLMError) as exc_info:
            asyncio.run(service._generate_gemini_with_retry.__wrapped__(service, "Prompt"))

    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)
