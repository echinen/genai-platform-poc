from fastapi import FastAPI
from src.middlewares.correlation_id import CorrelationIdMiddleware
from src.infra.database import engine
from src.infra.exception_handlers import setup_exception_handlers
from src.models.base import Base
from src.api.chat_controller import router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GenAI Platform",
    version="1.0.0"
)

@app.get("/health")
def health():

    return {
        "status": "ok"
    }

app.include_router(router)

app.add_middleware(
    CorrelationIdMiddleware
)

setup_exception_handlers(app)