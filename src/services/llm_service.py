import httpx
from datetime import timedelta
from typing import Any
from aiobreaker import CircuitBreaker, CircuitBreakerError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.infra.settings import settings
from src.infra.exceptions import ConfigException, LLMException


class NonRetryableLLMError(Exception):
    """Errors that should not trigger retry or circuit breaker accounting."""


GEMINI_CIRCUIT_BREAKER = CircuitBreaker(
    fail_max=3,
    timeout_duration=timedelta(seconds=60),
    exclude=[NonRetryableLLMError, ConfigException],
)


def _is_retryable_exception(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
            httpx.RemoteProtocolError,
        ),
    ):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code in (408, 409, 425, 429) or status_code >= 500

    return False


class LLMService:

    async def generate(
        self,
        prompt: str
    ) -> str:
        return await self._generate_gemini(prompt)

    async def _generate_gemini(
        self,
        prompt: str
    ) -> str:

        try:
            # Circuit breaker wraps the complete LLM call lifecycle for fast-fail during outages.
            return await GEMINI_CIRCUIT_BREAKER.call_async(
                self._generate_gemini_with_retry,
                prompt,
            )
        except CircuitBreakerError as exc:
            raise LLMException(
                message=(
                    "Servico de LLM temporariamente indisponivel. "
                    "Tente novamente em alguns instantes."
                ),
                status_code=503,
                error_code="LLM_CIRCUIT_OPEN",
            ) from exc
        except NonRetryableLLMError as exc:
            raise exc.__cause__ if exc.__cause__ else exc

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable_exception),
    )
    async def _generate_gemini_with_retry(
        self,
        prompt: str
    ) -> str:

        if not settings.gemini_api_key:
            raise ConfigException(
                "GEMINI_API_KEY não está configurada. Defina a variável de ambiente GEMINI_API_KEY."
            )

        headers = {
            "x-goog-api-key": settings.gemini_api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "model": settings.gemini_model,
            "input": prompt
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.gemini_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                return self._parse_gemini_response(response.json())
        except Exception as exc:
            if _is_retryable_exception(exc):
                raise
            raise NonRetryableLLMError() from exc

    def _parse_gemini_response(
        self,
        data: Any
    ) -> str:

        if isinstance(data, dict):
            steps = data.get("steps")
            if isinstance(steps, list):
                for step in steps:
                    if isinstance(step, dict) and step.get("type") == "model_output":
                        content = step.get("content")
                        if isinstance(content, list) and content:
                            first = content[0]
                            if isinstance(first, dict) and "text" in first:
                                return first["text"]

            candidates = data.get("candidates")
            if isinstance(candidates, list) and candidates:
                first = candidates[0]
                if isinstance(first, dict) and "output" in first:
                    return first["output"]

            if "output" in data:
                return data["output"]

        return str(data)
