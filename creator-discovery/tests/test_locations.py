"""Location parsing, canonicalization, and facet-ranking behavior."""
from app.utils.location import (
    infer_location,
    location_facet_counts,
    sanitize_location,
)
from app.utils.query_parse import parse_discovery_query


class TestAbbreviations:
    def test_query_with_la_extracts_location(self):
        parsed = parse_discovery_query("gamers in LA")
        assert parsed.location == "Los Angeles, CA"
        assert "gamer" in parsed.topic.lower()

    def test_other_city_abbreviations(self):
        assert infer_location("SD") == "San Diego, CA"
        assert infer_location("NYC") == "New York, NY"

    def test_lowercase_la_is_not_a_location(self):
        # "la" appears constantly in Spanish/French text — must not match.
        assert infer_location("viviendo la vida loca") is None

    def test_abbreviations_do_not_fire_inside_bios(self):
        # Whole-string only: "LV" in a fashion bio is Louis Vuitton, not Vegas;
        # "SD card" is storage, not San Diego.
        assert infer_location("Obsessed with LV & Chanel bags") is None
        assert infer_location("Best SD cards for creators") is None

    def test_iso_country_codes(self):
        assert sanitize_location("US") == "United States"
        assert sanitize_location("UK") == "United Kingdom"

    def test_ambiguous_state_codes_never_become_countries(self):
        # CA/IN/DE/ID are US states in bios — not Canada/India/Germany/Indonesia.
        for code in ("CA", "IN", "DE", "ID"):
            assert sanitize_location(code) is None, code
            assert infer_location(code) is None, code

    def test_lowercase_iso_words_are_not_countries(self):
        # "it", "us", "no", "be" are English words, not Italy/USA/Norway/Belgium.
        for word in ("it", "Us", "no", "be"):
            assert sanitize_location(word) is None, word
        assert infer_location("dream life and I'm living in it") is None
        assert infer_location("Daily vlogs from Us!") is None


class TestSanitize:
    def test_merges_city_variants(self):
        assert sanitize_location("Los Angeles") == "Los Angeles, CA"
        assert sanitize_location("Los Angeles, CA") == "Los Angeles, CA"

    def test_rejects_link_services_and_platforms(self):
        for junk in ("Linktree", "Fortnite", "Twitch", "Worldwide", "Online"):
            assert sanitize_location(junk) is None, junk

    def test_keeps_real_city_state(self):
        assert sanitize_location("Charleston, SC") == "Charleston, SC"


class TestFacetRanking:
    def test_ranked_by_count_with_variants_merged(self):
        values = (
            ["Los Angeles, CA"] * 5
            + ["Los Angeles"] * 3  # merges into LA
            + ["New York, NY"] * 4
            + ["Miami, FL"] * 2
        )
        facets = location_facet_counts(values)
        assert facets[0] == ("Los Angeles, CA", 8)
        assert facets[1] == ("New York, NY", 4)

    def test_junk_and_one_off_unknowns_hidden(self):
        values = ["Los Angeles, CA", "Grandma", "Linktree", "Grandma"]
        names = [n for n, _ in location_facet_counts(values)]
        assert names == ["Los Angeles, CA"]  # Grandma x2 < 3, Linktree junk

    def test_recurring_unknown_single_word_survives(self):
        # A real city we don't know about, listed by several creators.
        # (Single-word candidates must be >=6 chars to pass sanitize.)
        values = ["Pomona"] * 3
        assert location_facet_counts(values) == [("Pomona", 3)]

    def test_city_state_form_kept_even_once(self):
        values = ["Bastrop, TX"]
        assert location_facet_counts(values) == [("Bastrop, TX", 1)]

    def test_case_variants_corroborate_each_other(self):
        # "POMONA" + "Pomona" x2 = one entry with count 3, not two hidden ones.
        facets = location_facet_counts(["POMONA", "Pomona", "Pomona"])
        assert len(facets) == 1
        assert facets[0][1] == 3


class TestBackfillSafety:
    """The destructive backfill path must only touch whole-value junk."""

    class _Stub:
        def __init__(self, location, bio="", handle="someone"):
            self.location_text = location
            self.bio_text = bio
            self.handle = handle

    def _plan(self, location, bio=""):
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from backfill_locations import plan_change

        return plan_change(self._Stub(location, bio))

    def test_real_region_containing_blacklist_word_is_kept(self):
        # "Brecon Beacons" contains "beacons" (a link service) but IS a place.
        assert self._plan("Brecon Beacons") is None

    def test_postal_code_locations_are_kept(self):
        assert self._plan("Geneva 1204") is None

    def test_whole_value_junk_is_cleared(self):
        assert self._plan("Linktree") == ("clear-junk", None)

    def test_junk_with_bio_signal_is_reinferrred(self):
        assert self._plan("Linktree", bio="fitness coach based in Chicago") == (
            "re-infer",
            "Chicago, IL",
        )

    def test_unknown_but_plausible_is_never_overwritten_by_bio(self):
        # A real small town stays even when the bio mentions another city.
        assert self._plan("Petaluma", bio="often in New York") is None
