from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "GenAI Platform"

    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash"
    gemini_url: str = "https://generativelanguage.googleapis.com/v1beta/interactions"
    api_key: str

    database_url: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
