from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Supabase schema already exists; skip heavy migrations on serverless cold starts.
    if not os.getenv("VERCEL"):
        create_db_and_tables()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Creator Discovery MVP",
        description="Multi-platform creator discovery and classification engine",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/health")
    def health():
        db = "sqlite" if settings.is_sqlite else "supabase" if settings.is_supabase else "postgres"
        return {
            "status": "ok",
            "mock_llm": settings.use_mock_llm,
            "database": db,
        }

    return app


app = create_app()
