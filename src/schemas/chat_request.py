from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):

    user_id: str = Field(..., alias="userId")
    prompt: str

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Campo userId e obrigatorio e nao pode ser vazio.")
        return value.strip()

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Campo prompt e obrigatorio e nao pode ser vazio.")
        return value.strip()

    model_config = {
        "populate_by_name": True
    }
