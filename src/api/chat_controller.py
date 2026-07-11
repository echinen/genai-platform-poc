from datetime import timezone

from fastapi import APIRouter, Depends, Header
from httpx import HTTPStatusError

from src.schemas.chat_request import ChatRequest

from src.schemas.chat_response import ChatResponse

from src.services.chat_service import ChatService

from src.infra.exceptions import AppException
from src.infra.settings import settings

router = APIRouter()

service = ChatService()


def validate_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if x_api_key != settings.api_key:
        raise AppException(
            message="Nao autorizado. Informe uma API key valida.",
            status_code=401,
            error_code="UNAUTHORIZED"
        )

@router.post(
    "/v1/chat",
    response_model=ChatResponse
)
async def chat(
    request: ChatRequest,
    _: None = Depends(validate_api_key)
):
    try:
        entity = await service.process(
            request.user_id,
            request.prompt
        )

        created_at = entity.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        response = ChatResponse(
            id=entity.id,
            user_id=entity.user_id,
            prompt=entity.prompt,
            response=entity.response,
            model=entity.model,
            timestamp=created_at.isoformat().replace("+00:00", "Z")
        )

        return response.model_dump(by_alias=True)
    except AppException:
        raise
    except HTTPStatusError:
        raise