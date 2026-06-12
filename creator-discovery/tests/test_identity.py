import pytest

from app.models.account import Account
from app.models.creator import Creator
from app.models.enums import IdentityAction, Platform
from app.services.identity.resolver import resolve_identity


@pytest.mark.asyncio
async def test_identity_create_new(session):
    result = await resolve_identity(
        session,
        platform="Instagram",
        handle="brand_new_creator",
        display_name="Brand New",
        bio_text="A totally new creator",
    )
    assert result.recommended_action == IdentityAction.CREATE


@pytest.mark.asyncio
async def test_identity_attach_similar(session):
    creator = Creator(canonical_name="Jess | LA Fitness", home_region="Los Angeles, CA")
    session.add(creator)
    session.commit()
    session.refresh(creator)

    existing = Account(
        creator_id=creator.creator_id,
        platform=Platform.INSTAGRAM,
        handle="la_fitness_jess",
        display_name="Jess | LA Fitness",
        bio_text="Certified personal trainer Los Angeles",
        location_text="Los Angeles, CA",
    )
    session.add(existing)
    session.commit()

    result = await resolve_identity(
        session,
        platform="TikTok",
        handle="lafitjess",
        display_name="Jess LA Fit",
        bio_text="LA fitness creator gym vlogs",
        location_text="Los Angeles, CA",
    )
    assert result.recommended_action in (IdentityAction.ATTACH, IdentityAction.REVIEW)
    assert result.confidence > 0.3
