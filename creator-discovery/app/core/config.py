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

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

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
