from datetime import timezone

from fastapi import APIRouter
from httpx import HTTPStatusError

from src.schemas.chat_request import ChatRequest

from src.schemas.chat_response import ChatResponse

from src.services.chat_service import ChatService

from src.infra.exceptions import AppException

router = APIRouter()

service = ChatService()

@router.post(
    "/v1/chat",
    response_model=ChatResponse
)
async def chat(
    request: ChatRequest
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