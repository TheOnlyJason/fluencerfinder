import pytest

from app.api.routes.accounts import _apply_account_filters
from app.models.account import Account
from app.models.enums import Platform
from sqlmodel import Session, select, SQLModel, create_engine


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add_all([
            Account(
                platform=Platform.TIKTOK,
                handle="small",
                niche="gaming",
                follower_count=25_000,
                location_text="Los Angeles, CA",
            ),
            Account(
                platform=Platform.TIKTOK,
                handle="mid",
                niche="gaming",
                follower_count=55_000,
                location_text="Los Angeles, CA",
            ),
            Account(platform=Platform.TIKTOK, handle="big", niche="fitness", follower_count=250_000),
            Account(platform=Platform.TIKTOK, handle="unknown", niche="gaming", follower_count=None),
        ])
        s.commit()
        yield s


def test_filter_by_gamer_niche_matches_gaming(session):
    stmt = _apply_account_filters(
        select(Account),
        niche="gamer",
        location="Los Angeles, CA",
        min_followers=10_000,
        max_followers=100_000,
    )
    handles = {a.handle for a in session.exec(stmt).all()}
    assert handles == {"small", "mid"}


def test_filter_by_follower_range(session):
    stmt = _apply_account_filters(select(Account), niche="gaming", min_followers=10_000, max_followers=100_000)
    handles = {a.handle for a in session.exec(stmt).all()}
    assert handles == {"small", "mid"}


def test_filter_min_followers_only(session):
    stmt = _apply_account_filters(select(Account), min_followers=50_000)
    handles = {a.handle for a in session.exec(stmt).all()}
    assert handles == {"mid", "big"}
