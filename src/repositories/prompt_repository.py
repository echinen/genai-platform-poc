from sqlalchemy.orm import Session

from src.models.prompt_history import PromptHistory

class PromptRepository:

    def save(
        self,
        db: Session,
        entity: PromptHistory
    ):

        db.add(entity)

        db.commit()

        db.refresh(entity)

        return entity
    