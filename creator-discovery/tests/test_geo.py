"""Geo gazetteer + center-resolution (the pure, SQLite-safe parts of radius search).

The earthdistance query itself is Postgres-only (no-op on SQLite), so these cover
geocoding, place lookup, and the "near" center parsing that the review flagged.
"""
from app.data.place_coords import PLACE_COORDS, RADIUS_PRECISIONS, geocode_place, searchable_places
from app.api.routes.accounts import _resolve_center
from app.utils.location import _CANONICAL_VALUES


def test_every_canonical_location_has_coordinates():
    missing = [v for v in _CANONICAL_VALUES if v not in PLACE_COORDS]
    assert missing == [], f"canonical values without coords: {missing}"


def test_coords_are_in_range_and_precision_valid():
    valid = {"city", "metro", "region", "country"}
    for name, c in PLACE_COORDS.items():
        assert -90 <= c.lat <= 90 and -180 <= c.lng <= 180, name
        assert c.precision in valid, name


def test_geocode_place_handles_variants():
    assert geocode_place("Los Angeles, CA").precision == "city"
    assert geocode_place("Los Angeles") == geocode_place("Los Angeles, CA")  # canonicalized
    assert geocode_place("NYC").lat == PLACE_COORDS["New York, NY"].lat
    assert geocode_place("definitely not a place") is None
    assert geocode_place(None) is None


def test_searchable_places_are_only_city_metro():
    names = searchable_places()
    assert "Los Angeles, CA" in names
    # Countries/regions are too coarse to be a radius center.
    assert "United States" not in names
    assert "California" not in names
    assert all(PLACE_COORDS[n].precision in RADIUS_PRECISIONS for n in names)


class TestResolveCenter:
    def test_place_name(self):
        lat, lng, label = _resolve_center("Los Angeles, CA")
        assert round(lat, 2) == 34.05 and label == "Los Angeles, CA"

    def test_city_state_is_not_parsed_as_coordinates(self):
        # "Austin, TX" has a comma but is NOT lat,lng — must geocode, not crash.
        lat, lng, _ = _resolve_center("Austin, TX")
        assert round(lat, 2) == 30.27

    def test_explicit_lat_lng(self):
        assert _resolve_center("34.05, -118.24") == (34.05, -118.24, "34.05, -118.24")

    def test_out_of_range_coords_rejected(self):
        assert _resolve_center("999, 999") is None

    def test_unknown_place_returns_none(self):
        assert _resolve_center("Zzznowhere") is None

    def test_coarse_place_rejected_as_center(self):
        # A country isn't specific enough to anchor a radius.
        assert _resolve_center("United States") is None
