import pytest

from app.models.account import Account
from app.models.enums import Platform
from app.schemas.search import SearchRequest
from app.services.discovery.service import search_creators
from app.utils.fts import sync_account_fts


@pytest.mark.asyncio
async def test_database_first_search(session):
    account = Account(
        platform=Platform.INSTAGRAM,
        handle="la_fitness_jess",
        display_name="Jess | LA Fitness",
        bio_text="Certified personal trainer Los Angeles",
        niche="fitness",
        location_text="Los Angeles, CA",
        channel_type="fitness",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    sync_account_fts(session, account)
    session.commit()

    request = SearchRequest(
        query="Los Angeles fitness creators",
        use_external_providers=False,
        limit=10,
    )
    response = await search_creators(session, request)
    assert response.total >= 1
    assert any("fitness" in (r.account.niche or "") for r in response.results)


@pytest.mark.asyncio
async def test_mock_provider_discovery(session):
    from app.services.providers.mock_provider import MockDiscoveryProvider

    request = SearchRequest(
        query="Los Angeles fitness",
        use_external_providers=True,
        limit=10,
    )
    response = await search_creators(session, request, providers=[MockDiscoveryProvider()])
    assert response.from_providers >= 0
    assert response.total >= 1
