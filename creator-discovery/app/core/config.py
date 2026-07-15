from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./data/creator_discovery.db"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_db_password: str = ""
    supabase_pooler_host: str = ""
    supabase_pooler_port: int = 5432
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    min_local_results: int = 3
    tavily_api_key: str = ""
    youtube_api_key: str = ""
    use_mock_discovery: bool = False
    # Privacy: when False (default), scraped contact emails are stripped from all
    # API responses and exports so a public deployment never leaks them. Set to
    # True only on a private/trusted instance where you need emails for outreach.
    expose_contact_emails: bool = False

    # Security. Write/paid endpoints require a valid Supabase session token when
    # Supabase is configured; admin endpoints additionally require the caller's
    # email to be in this comma-separated allowlist (anyone can self-sign-up, so
    # "logged in" alone must not authorize bulk/paid operations).
    admin_emails: str = ""
    # Per-user requests/minute for the paid /search endpoint (in-memory limiter).
    search_rate_limit_per_min: int = 20
    # Minimum cosine similarity for a semantic-ONLY hit to enter search results
    # (keyword-matched accounts are unaffected). Measured on real data:
    # on-topic accounts score ≥0.44 for text-embedding-3-small; off-topic
    # "similar vibe" profiles (the gym-people-for-a-gamers-query leak) < 0.44.
    semantic_min_similarity: float = 0.44
    # Expose interactive API docs (/docs, /openapi.json). Off in production by
    # default; auto-on for local SQLite dev.
    enable_docs: bool = False

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_list(self) -> List[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    @property
    def auth_enabled(self) -> bool:
        # Enforce auth whenever Supabase is configured (i.e. the real backend);
        # local SQLite dev / the test suite run without it.
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def use_mock_llm(self) -> bool:
        return not self.openai_api_key

    @property
    def resolved_database_url(self) -> str:
        if self.supabase_url and self.supabase_db_password:
            ref = (
                self.supabase_url.replace("https://", "")
                .replace("http://", "")
                .removesuffix(".supabase.co")
                .strip("/")
            )
            if self.supabase_pooler_host:
                # Shared pooler (IPv4) — copy host from Dashboard → Database → Connection string
                return (
                    f"postgresql://postgres.{ref}:{self.supabase_db_password}"
                    f"@{self.supabase_pooler_host}:{self.supabase_pooler_port}/postgres"
                    f"?sslmode=require"
                )
            # Direct connection (IPv6 only on many projects — prefer pooler)
            return (
                f"postgresql://postgres:{self.supabase_db_password}"
                f"@db.{ref}.supabase.co:5432/postgres?sslmode=require"
            )
        if self.database_url.startswith("postgresql"):
            return self.database_url
        return self.database_url

    @property
    def is_sqlite(self) -> bool:
        return self.resolved_database_url.startswith("sqlite")

    @property
    def is_supabase(self) -> bool:
        return "supabase.co" in self.resolved_database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
