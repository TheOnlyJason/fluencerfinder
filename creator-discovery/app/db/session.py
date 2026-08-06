import logging
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

if settings.is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # Fail fast instead of hanging forever if the database is unreachable. Without
    # this, a stalled connection during startup blocks uvicorn from ever serving
    # any request (including /health), which looks like the backend being "down".
    connect_args = {"connect_timeout": 10}
engine = create_engine(
    settings.resolved_database_url,
    echo=False,
    connect_args=connect_args,
    pool_pre_ping=True,
)


def create_db_and_tables() -> None:
    # Startup must never hang or crash on a DB hiccup, otherwise the whole API
    # (including /health) becomes unreachable. Log and continue so the service
    # still boots; the Supabase schema already exists in production.
    try:
        SQLModel.metadata.create_all(engine)
        _migrate_schema()
        _setup_fts()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Skipping DB init (continuing startup): %s", exc)


def _migrate_schema() -> None:
    """Add columns to existing tables (create_all does not alter Postgres/Supabase)."""
    new_columns = [
        ("follower_count", "INTEGER"),
        ("contact_email", "VARCHAR"),
        # Geo (radius search) — city-centroid coordinates from location_text.
        ("latitude", "DOUBLE PRECISION"),
        ("longitude", "DOUBLE PRECISION"),
        ("geo_precision", "VARCHAR"),
        ("geocoded_at", "TIMESTAMP"),
    ]
    with engine.connect() as conn:
        if settings.is_sqlite:
            cols = conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()
            names = {row[1] for row in cols}
            for col, sql_type in new_columns:
                if col not in names:
                    conn.exec_driver_sql(f"ALTER TABLE accounts ADD COLUMN {col} {sql_type}")
        else:
            # Don't let an ALTER TABLE wait forever on a table lock during startup.
            conn.exec_driver_sql("SET lock_timeout = '5s'")
            conn.exec_driver_sql("SET statement_timeout = '10s'")
            for col, sql_type in new_columns:
                conn.exec_driver_sql(
                    f"ALTER TABLE accounts ADD COLUMN IF NOT EXISTS {col} {sql_type}"
                )
        conn.commit()


def _setup_fts() -> None:
    """Create full-text search indexes for SQLite."""
    if not settings.is_sqlite:
        return
    with engine.connect() as conn:
        conn.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS accounts_fts USING fts5(
                account_id UNINDEXED,
                handle,
                display_name,
                bio_text,
                niche,
                secondary_niches,
                hobbies,
                location_text,
                channel_type,
                tokenize='porter'
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS creators_fts USING fts5(
                creator_id UNINDEXED,
                canonical_name,
                home_region,
                overall_topics,
                tokenize='porter'
            )
            """
        )
        conn.commit()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
