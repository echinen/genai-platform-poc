from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import httpx
import logging

from src.infra.exceptions import AppException

logger = logging.getLogger(__name__)
CORRELATION_ID_HEADER = "X-Correlation-Id"


def _get_correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[dict] | None = None
) -> JSONResponse:
    correlation_id = _get_correlation_id(request)

    error_payload: dict = {
        "code": code,
        "message": message,
        "path": str(request.url.path)
    }

    if correlation_id:
        error_payload["correlationId"] = correlation_id

    if details is not None:
        error_payload["details"] = details

    response = JSONResponse(
        status_code=status_code,
        content={"error": error_payload}
    )

    if correlation_id:
        response.headers[CORRELATION_ID_HEADER] = correlation_id

    return response


async def app_exception_handler(
    request: Request,
    exc: AppException
) -> JSONResponse:
    """Handle custom application exceptions."""
    return _error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.error_code,
        message=exc.message
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI/Pydantic request validation errors."""
    details = []
    for err in exc.errors():
        details.append(
            {
                "field": ".".join(str(item) for item in err.get("loc", []) if item != "body"),
                "message": err.get("msg", "Valor inválido")
            }
        )

    return _error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Dados de entrada inválidos.",
        details=details
    )


async def httpx_exception_handler(
    request: Request,
    exc: httpx.HTTPStatusError
) -> JSONResponse:
    """Handle httpx HTTP errors from external APIs."""
    status_code = exc.response.status_code
    reason = exc.response.reason_phrase or "Unknown Error"

    # Map common HTTP errors to user-friendly messages
    message_map = {
        401: "Erro de autenticação com o provedor LLM. Verifique sua chave de API.",
        403: "Acesso negado pelo provedor LLM. Verifique suas permissões.",
        404: "Modelo ou endpoint não encontrado no provedor LLM.",
        429: "Limite de requisições excedido. Tente novamente em alguns segundos.",
        500: "Erro interno no provedor LLM. Tente novamente mais tarde.",
        503: "Provedor LLM indisponível no momento. Tente novamente mais tarde.",
    }

    message = message_map.get(
        status_code,
        f"Erro ao comunicar com provedor LLM: {reason}"
    )

    logger.error(
        f"LLM Provider Error: {status_code} {reason}",
        extra={
            "url": str(exc.request.url),
            "response": exc.response.text[:500],
            "correlation_id": _get_correlation_id(request)
        }
    )

    return _error_response(
        request=request,
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="LLM_PROVIDER_ERROR",
        message=message
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={
            "path": str(request.url.path),
            "correlation_id": _get_correlation_id(request)
        }
    )

    return _error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message="Erro interno do servidor. Tente novamente mais tarde."
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup all exception handlers for the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(httpx.HTTPStatusError, httpx_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
