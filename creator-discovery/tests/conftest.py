import pytest
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine


def _setup_test_fts(engine):
    with engine.connect() as conn:
        conn.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS accounts_fts USING fts5(
                account_id UNINDEXED, handle, display_name, bio_text, niche,
                secondary_niches, hobbies, location_text, channel_type,
                tokenize='porter'
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS creators_fts USING fts5(
                creator_id UNINDEXED, canonical_name, home_region, overall_topics,
                tokenize='porter'
            )
            """
        )
        conn.commit()


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    _setup_test_fts(engine)
    with Session(engine) as session:
        yield session
