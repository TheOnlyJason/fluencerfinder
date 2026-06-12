import pytest

from app.models.enums import Platform
from app.utils.profile_extract import extract_profiles_from_results, profile_from_url


def test_profile_from_instagram_url():
    account = profile_from_url(
        "https://www.instagram.com/fitness_trainer_la/",
        title="LA Fitness Trainer",
        snippet="Personal trainer in Los Angeles",
    )
    assert account is not None
    assert account.platform == Platform.INSTAGRAM
    assert account.handle == "fitness_trainer_la"
    assert account.display_name == "LA Fitness Trainer"


def test_profile_from_tiktok_url():
    account = profile_from_url("https://www.tiktok.com/@matcha.girl")
    assert account is not None
    assert account.platform == Platform.TIKTOK
    assert account.handle == "matcha.girl"


def test_skips_non_profile_urls():
    assert profile_from_url("https://www.instagram.com/explore/tags/fitness/") is None
    assert profile_from_url("https://www.instagram.com/p/ABC123/") is None
    assert profile_from_url("https://www.tiktok.com/discover/fitness") is None


def test_extract_deduplicates():
    results = [
        {"url": "https://www.instagram.com/creator_one/", "title": "One"},
        {"url": "https://instagram.com/creator_one", "title": "One duplicate"},
        {"url": "https://x.com/creator_two", "title": "Two"},
    ]
    accounts = extract_profiles_from_results(results)
    assert len(accounts) == 2
    handles = {a.handle for a in accounts}
    assert "creator_one" in handles
    assert "creator_two" in handles
