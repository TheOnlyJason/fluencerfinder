"""Tests for YouTube caption niche inference."""
from app.services.enrichment.youtube_captions import infer_niche_from_caption_text


def test_infer_gaming_niche():
    text = (
        "Welcome to my gaming channel. Today we play minecraft and fortnite "
        "with epic playthrough highlights and esports commentary."
    )
    assert infer_niche_from_caption_text(text) == "gaming"


def test_infer_food_niche():
    text = "In this video I share my favorite recipe for meal prep and cooking in the kitchen."
    assert infer_niche_from_caption_text(text) == "food"


def test_infer_returns_none_for_sparse_text():
    assert infer_niche_from_caption_text("hello world") is None
