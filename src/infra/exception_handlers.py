from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import httpx
import logging

from src.infra.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(
    request: Request,
    exc: AppException
) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "path": str(request.url.path)
            }
        }
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

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Dados de entrada inválidos.",
                "path": str(request.url.path),
                "details": details
            }
        }
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
        extra={"url": str(exc.request.url), "response": exc.response.text[:500]}
    )

    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": {
                "code": "LLM_PROVIDER_ERROR",
                "message": message,
                "path": str(request.url.path)
            }
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected error: {str(exc)}",
        exc_info=True,
        extra={"path": str(request.url.path)}
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Erro interno do servidor. Tente novamente mais tarde.",
                "path": str(request.url.path)
            }
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup all exception handlers for the FastAPI application."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(httpx.HTTPStatusError, httpx_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
