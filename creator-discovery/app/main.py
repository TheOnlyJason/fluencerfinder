from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Supabase schema already exists; skip heavy migrations on serverless/managed
    # cold starts (Vercel, Cloud Run sets K_SERVICE) to keep startup fast. Set
    # SKIP_DB_INIT=1 to force-skip anywhere.
    skip = os.getenv("VERCEL") or os.getenv("K_SERVICE") or os.getenv("SKIP_DB_INIT")
    if not skip:
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
    # Public read API (no cookies/auth), so allow any origin. This avoids CORS
    # edge cases with Cloudflare workers.dev / pages.dev / custom domains.
    # allow_credentials must be False when allow_origins is ["*"].
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
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
