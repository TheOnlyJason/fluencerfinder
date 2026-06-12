from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.is_sqlite else {}
engine = create_engine(
    settings.resolved_database_url, echo=False, connect_args=connect_args
)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_schema()
    _setup_fts()


def _migrate_schema() -> None:
    """Add columns to existing tables (create_all does not alter Postgres/Supabase)."""
    new_columns = [
        ("follower_count", "INTEGER"),
        ("contact_email", "VARCHAR"),
    ]
    with engine.connect() as conn:
        if settings.is_sqlite:
            cols = conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()
            names = {row[1] for row in cols}
            for col, sql_type in new_columns:
                if col not in names:
                    conn.exec_driver_sql(f"ALTER TABLE accounts ADD COLUMN {col} {sql_type}")
        else:
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
