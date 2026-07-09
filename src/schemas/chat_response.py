from pydantic import BaseModel, Field


class ChatResponse(BaseModel):

    id: int
    user_id: str = Field(..., alias="userId")
    prompt: str
    response: str
    model: str
    timestamp: str

    model_config = {
        "populate_by_name": True
    }
