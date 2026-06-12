from app.models.enums import Platform
from app.utils.youtube import (
    build_youtube_profile_url,
    format_display_handle,
    is_youtube_channel_id,
)


def test_build_youtube_profile_url_prefers_stored_user_link():
    links = "youtube_channel_id=UCxxx; https://www.youtube.com/user/marquesbrownlee; source=rightfluencer"
    url = build_youtube_profile_url("marquesbrownlee", external_links=links)
    assert url == "https://www.youtube.com/user/marquesbrownlee"


def test_build_youtube_profile_url_uses_channel_id():
    url = build_youtube_profile_url("marquesbrownlee", channel_id="UCBJycsmduvYEL83R_U4JriQ")
    assert url == "https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ"


def test_build_youtube_profile_url_defaults_to_user_path():
    url = build_youtube_profile_url("marquesbrownlee")
    assert url == "https://www.youtube.com/user/marquesbrownlee"


def test_is_youtube_channel_id():
    assert is_youtube_channel_id("UCYzPXprvl5Y-Sf0g4vX-m6g")
    assert not is_youtube_channel_id("jacksepticeye")


def test_format_display_handle_uses_name_for_channel_id():
    handle = format_display_handle(
        Platform.YOUTUBE,
        "ucyzpxprvl5ysfog4vxm6g",
        "Jacksepticeye",
    )
    assert handle == "jacksepticeye"
