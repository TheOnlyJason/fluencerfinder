import pytest

from app.models.enums import Platform
from app.utils.followers import format_follower_count, parse_follower_count


def test_parse_instagram_followers():
    text = "Fitness King Of LA... DM for Training. 55K Followers, 1,620 Following, 68 Posts"
    assert parse_follower_count(text) == 55_000


def test_parse_subscribers():
    assert parse_follower_count("1.2M subscribers on YouTube") == 1_200_000


def test_format_followers():
    assert format_follower_count(55_000, Platform.INSTAGRAM) == "55K followers"
    assert format_follower_count(1_200_000, Platform.YOUTUBE) == "1.2M subscribers"


def test_ignores_following():
    assert parse_follower_count("1,620 Following only") is None
