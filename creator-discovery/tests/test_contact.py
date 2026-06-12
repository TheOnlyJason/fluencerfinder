import pytest

from app.utils.contact import parse_email, parse_location


def test_parse_email_from_bio():
    assert parse_email("Contact: hello@brand.com for collabs") == "hello@brand.com"
    assert parse_email("DM me on instagram") is None


def test_parse_email_blocks_platform_domains():
    assert parse_email("email: support@instagram.com") is None


def test_parse_location_from_bio():
    loc = parse_location("Certified trainer based in Los Angeles, CA")
    assert loc and "Los Angeles" in loc
    assert parse_location("Creator from Tokyo sharing anime content") == "Tokyo, Japan"
