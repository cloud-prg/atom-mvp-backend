from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, chat, conversations, search


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "env": settings.app_env,
            "demo_mode": settings.demo_mode,
            "mock_ai": settings.use_mock_ai,
            "mock_search": settings.use_mock_search,
        }

    app.include_router(auth.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    return app


app = create_app()

