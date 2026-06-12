from app.utils.query_parse import parse_discovery_query


def test_parse_gamer_la_follower_range():
    parsed = parse_discovery_query(
        "gamer in los angeles that has more than 10 k follower but less than 100K"
    )
    assert parsed.topic.lower() == "gamer"
    assert parsed.location and "Los Angeles" in parsed.location
    assert parsed.min_followers == 10_000
    assert parsed.max_followers == 100_000
    assert "gamer" in parsed.provider_query
    assert "Los Angeles" in parsed.provider_query


def test_parse_between_syntax():
    parsed = parse_discovery_query("fitness creators in Miami between 5K and 50K followers")
    assert "fitness" in parsed.topic
    assert parsed.location and "Miami" in parsed.location
    assert parsed.min_followers == 5_000
    assert parsed.max_followers == 50_000


def test_parse_range_dash():
    parsed = parse_discovery_query("beauty influencer NYC 10K-100K")
    assert parsed.min_followers == 10_000
    assert parsed.max_followers == 100_000


def test_gamer_matches_gaming_niche():
    from app.utils.query_parse import account_matches_criteria, expand_topic_terms

    assert "gaming" in expand_topic_terms("gamer")

    class Acc:
        niche = "gaming"
        handle = "inviicta"
        display_name = None
        bio_text = None
        channel_type = None
        hobbies = None
        secondary_niches = None
        location_text = "Los Angeles, CA"
        follower_count = 50_000

    assert account_matches_criteria(
        Acc(),
        topic="gamer",
        location="Los Angeles, CA",
        min_followers=10_000,
        max_followers=100_000,
    )


def test_parse_topic_only():
    parsed = parse_discovery_query("tft content creator")
    assert parsed.topic == "tft content"
    assert parsed.min_followers is None
