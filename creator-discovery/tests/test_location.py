from app.utils.location import infer_location, sanitize_location


def test_explicit_bio_location():
    loc = infer_location("Certified trainer based in Los Angeles, CA")
    assert loc and "Los Angeles" in loc


def test_from_city_pattern():
    assert infer_location("Creator from Tokyo sharing anime content") == "Tokyo, Japan"


def test_sports_team_hint():
    assert infer_location("Huge Lakers fan | fitness tips") == "Los Angeles, CA"


def test_hashtag_location():
    assert infer_location("Daily vlogs #nyc #foodie") == "New York, NY"


def test_handle_hint():
    assert infer_location(handle="nyc_foodie_jane") == "New York, NY"


def test_flag_country():
    assert infer_location("Travel blogger 🇯🇵 anime & culture") == "Japan"


def test_youtube_country_code():
    assert infer_location("US") == "United States"


def test_phone_area_code():
    assert infer_location("Bookings: (310) 555-0199") == "Los Angeles, CA"


def test_landmark_hint():
    assert infer_location("Walking tours around Times Square") == "New York, NY"


def test_rejects_garbage_locations():
    assert infer_location("videos from their smartphones") is None
    assert infer_location("2015 to 2025 kevin@acdanything.com") is None
    assert infer_location('veoko (@vveoko): "Enter to win an NZXT Player 2 PC packed wi') is None
    assert sanitize_location("their smartphones") is None
    assert sanitize_location("John Fogerty") is None
    assert sanitize_location("Honolulu") == "Honolulu, HI"
