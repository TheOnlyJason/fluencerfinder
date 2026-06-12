import pytest

from app.models.account import Account
from app.models.enums import Platform
from app.services.classification.classifier import classify_account, profile_content_hash


@pytest.mark.asyncio
async def test_mock_classification(session):
    account = Account(
        platform=Platform.INSTAGRAM,
        handle="la_fitness_jess",
        display_name="Jess | LA Fitness",
        bio_text="Certified personal trainer Los Angeles workouts",
        location_text="Los Angeles, CA",
    )
    session.add(account)
    session.commit()
    session.refresh(account)

    result, skipped = await classify_account(session, account)
    assert not skipped
    assert result.primary_niche in ("fitness", "personal training")
    assert account.niche == "fitness"
    assert account.classification_hash == profile_content_hash(account)


@pytest.mark.asyncio
async def test_skip_reclassification(session):
    account = Account(
        platform=Platform.INSTAGRAM,
        handle="test_user",
        bio_text="Fitness content",
        niche="fitness",
        classification_hash=profile_content_hash(Account(
            platform=Platform.INSTAGRAM,
            handle="test_user",
            bio_text="Fitness content",
        )),
    )
    session.add(account)
    session.commit()
    session.refresh(account)

    result, skipped = await classify_account(session, account)
    assert skipped
    assert "Reused" in result.reasoning
