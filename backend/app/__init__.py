from fastapi import FastAPI

from .routes.chat import router as chat_router
from .routes.doctor import router as doctor_router


def create_app() -> FastAPI:
    app = FastAPI(title="Doctor Assistant MCP Backend")
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(doctor_router, prefix="/api/doctor", tags=["doctor"])
    return app


