from time import time

from src.infra.database import SessionLocal
from src.infra.settings import settings

from src.repositories.prompt_repository import PromptRepository

from src.models.prompt_history import PromptHistory

from src.services.llm_service import LLMService

class ChatService:

    def __init__(self):

        self.repository = PromptRepository()

        self.llm = LLMService()

    async def process(
        self,
        user_id: str,
        prompt: str
    ):

        db = SessionLocal()

        entity = PromptHistory(
            user_id=user_id,
            prompt=prompt,
            response="",
            model=settings.gemini_model,
            status="PENDING",
            processing_time_ms=0
        )

        self.repository.save(
            db,
            entity
        )

        start = time()

        try:
            response = await self.llm.generate(
                prompt
            )

            elapsed = int(
                (time() - start) * 1000
            )

            entity.response = response
            entity.status = "SUCCESS"
            entity.processing_time_ms = elapsed

            db.commit()
            db.refresh(entity)

            return entity
        except Exception:
            entity.status = "FAILED"
            db.commit()
            db.refresh(entity)
            raise
        finally:
            db.close()
    