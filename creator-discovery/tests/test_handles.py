from app.models.enums import Platform
from app.utils.handles import (
    build_profile_url,
    handle_similarity,
    normalize_handle,
    parse_profile_url,
    strip_handle,
)


def test_normalize_handle():
    assert normalize_handle("@Fitness_Girl") == "fitness_girl"
    assert normalize_handle("  @user.name  ") == "user.name"


def test_strip_handle():
    assert strip_handle("@hello") == "hello"


def test_handle_similarity():
    assert handle_similarity("fitness_girl", "@Fitness_Girl") == 1.0
    assert handle_similarity("lafitjess", "la_fitness_jess") > 0.5


def test_parse_profile_url():
    plat, handle = parse_profile_url("https://www.instagram.com/la_fitness_jess/")
    assert plat == Platform.INSTAGRAM
    assert handle == "la_fitness_jess"

    plat, handle = parse_profile_url("https://www.tiktok.com/@lafitjess")
    assert plat == Platform.TIKTOK
    assert handle == "lafitjess"

    plat, handle = parse_profile_url("https://x.com/tokyo_fashion_aya")
    assert plat == Platform.X
    assert handle == "tokyo_fashion_aya"


def test_build_profile_url():
    url = build_profile_url(Platform.INSTAGRAM, "testuser")
    assert "instagram.com/testuser" in url

    yt = build_profile_url(Platform.YOUTUBE, "marquesbrownlee")
    assert yt == "https://www.youtube.com/user/marquesbrownlee"


def test_parse_youtube_user_url():
    plat, handle = parse_profile_url("https://www.youtube.com/user/marquesbrownlee")
    assert plat == Platform.YOUTUBE
    assert handle == "marquesbrownlee"
