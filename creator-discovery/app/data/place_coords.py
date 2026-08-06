"""Bundled gazetteer: canonical place strings → (latitude, longitude, precision).

City-centroid coordinates for every canonical value location.py can emit, plus
recurring real places seen in the catalog. Bundled (no runtime geocoding API):
deterministic, offline, $0. Coordinates are city centroids (±~1 km) — fine for
"creators within N miles" at city-level honesty.

precision:
  "city"    — a specific city; usable for radius search
  "metro"   — a metro area (Bay Area, Orange County); usable, but broad
  "region"  — a state/large region; too coarse for radius search
  "country" — too coarse for radius search

Sources: standard public city centroids (OSM/Wikipedia), hand-verified.
"""
from __future__ import annotations

from typing import NamedTuple, Optional


class PlaceCoord(NamedTuple):
    lat: float
    lng: float
    precision: str  # city | metro | region | country


PLACE_COORDS: dict[str, PlaceCoord] = {
    # --- US cities ---
    "Los Angeles, CA": PlaceCoord(34.0522, -118.2437, "city"),
    "San Francisco, CA": PlaceCoord(37.7749, -122.4194, "city"),
    "San Diego, CA": PlaceCoord(32.7157, -117.1611, "city"),
    "San Jose, CA": PlaceCoord(37.3382, -121.8863, "city"),
    "Sacramento, CA": PlaceCoord(38.5816, -121.4944, "city"),
    "Long Beach, CA": PlaceCoord(33.7701, -118.1937, "city"),
    "Anaheim, CA": PlaceCoord(33.8366, -117.9143, "city"),
    "Irvine, CA": PlaceCoord(33.6846, -117.8265, "city"),
    "Oakland, CA": PlaceCoord(37.8044, -122.2712, "city"),
    "Calabasas, CA": PlaceCoord(34.1367, -118.6615, "city"),
    "Agoura Hills, CA, USA": PlaceCoord(34.1533, -118.7617, "city"),
    "New York, NY": PlaceCoord(40.7128, -74.0060, "city"),
    "Kingston, NY": PlaceCoord(41.9270, -73.9974, "city"),
    "Jersey City, NJ": PlaceCoord(40.7178, -74.0431, "city"),
    "Las Vegas, NV": PlaceCoord(36.1699, -115.1398, "city"),
    "Salt Lake City, UT": PlaceCoord(40.7608, -111.8910, "city"),
    "Kansas City, MO": PlaceCoord(39.0997, -94.5786, "city"),
    "San Antonio, TX": PlaceCoord(29.4241, -98.4936, "city"),
    "Fort Worth, TX": PlaceCoord(32.7555, -97.3308, "city"),
    "Austin, TX": PlaceCoord(30.2672, -97.7431, "city"),
    "Dallas, TX": PlaceCoord(32.7767, -96.7970, "city"),
    "Houston, TX": PlaceCoord(29.7604, -95.3698, "city"),
    "Atlanta, GA": PlaceCoord(33.7490, -84.3880, "city"),
    "East Point, GA": PlaceCoord(33.6796, -84.4394, "city"),
    "Boston, MA": PlaceCoord(42.3601, -71.0589, "city"),
    "Chicago, IL": PlaceCoord(41.8781, -87.6298, "city"),
    "Denver, CO": PlaceCoord(39.7392, -104.9903, "city"),
    "Detroit, MI": PlaceCoord(42.3314, -83.0458, "city"),
    "Miami, FL": PlaceCoord(25.7617, -80.1918, "city"),
    "Orlando, FL": PlaceCoord(28.5384, -81.3789, "city"),
    "Tampa, FL": PlaceCoord(27.9506, -82.4572, "city"),
    "Seattle, WA": PlaceCoord(47.6062, -122.3321, "city"),
    "Portland, OR": PlaceCoord(45.5152, -122.6784, "city"),
    "Phoenix, AZ": PlaceCoord(33.4484, -112.0740, "city"),
    "Philadelphia, PA": PlaceCoord(39.9526, -75.1652, "city"),
    "Nashville, TN": PlaceCoord(36.1627, -86.7816, "city"),
    "Minneapolis, MN": PlaceCoord(44.9778, -93.2650, "city"),
    "Charlotte, NC": PlaceCoord(35.2271, -80.8431, "city"),
    "Raleigh, NC": PlaceCoord(35.7796, -78.6382, "city"),
    "New Bern, NC": PlaceCoord(35.1085, -77.0441, "city"),
    "Pittsburgh, PA": PlaceCoord(40.4406, -79.9959, "city"),
    "Cleveland, OH": PlaceCoord(41.4993, -81.6944, "city"),
    "Columbus, OH": PlaceCoord(39.9612, -82.9988, "city"),
    "Cincinnati, OH": PlaceCoord(39.1031, -84.5120, "city"),
    "Indianapolis, IN": PlaceCoord(39.7684, -86.1581, "city"),
    "Baltimore, MD": PlaceCoord(39.2904, -76.6122, "city"),
    "Washington, DC": PlaceCoord(38.9072, -77.0369, "city"),
    "Honolulu, HI": PlaceCoord(21.3099, -157.8581, "city"),
    "New Orleans, LA": PlaceCoord(29.9511, -90.0715, "city"),
    "Charleston, SC": PlaceCoord(32.7765, -79.9311, "city"),

    # --- US metros / regions ---
    "San Francisco Bay Area, CA": PlaceCoord(37.7749, -122.4194, "metro"),
    "Orange County, CA": PlaceCoord(33.7175, -117.8311, "metro"),
    "Southern California": PlaceCoord(34.0522, -118.2437, "region"),
    "California": PlaceCoord(36.7783, -119.4179, "region"),
    "Florida": PlaceCoord(27.6648, -81.5158, "region"),
    "Texas": PlaceCoord(31.9686, -99.9018, "region"),
    "Colorado": PlaceCoord(39.5501, -105.7821, "region"),
    "Arizona": PlaceCoord(34.0489, -111.0937, "region"),
    "Georgia": PlaceCoord(32.1656, -82.9001, "region"),
    "Hawaii": PlaceCoord(20.7984, -156.3319, "region"),

    # --- International cities ---
    "London, UK": PlaceCoord(51.5074, -0.1278, "city"),
    "Manchester, UK": PlaceCoord(53.4808, -2.2426, "city"),
    "Birmingham, UK": PlaceCoord(52.4862, -1.8904, "city"),
    "Edinburgh, UK": PlaceCoord(55.9533, -3.1883, "city"),
    "Leeds, UK": PlaceCoord(53.8008, -1.5491, "city"),
    "Dublin": PlaceCoord(53.3498, -6.2603, "city"),
    "Paris, France": PlaceCoord(48.8566, 2.3522, "city"),
    "Berlin, Germany": PlaceCoord(52.5200, 13.4050, "city"),
    "Munich, Germany": PlaceCoord(48.1351, 11.5820, "city"),
    "Amsterdam, Netherlands": PlaceCoord(52.3676, 4.9041, "city"),
    "Barcelona, Spain": PlaceCoord(41.3874, 2.1686, "city"),
    "Madrid, Spain": PlaceCoord(40.4168, -3.7038, "city"),
    "Milan, Italy": PlaceCoord(45.4642, 9.1900, "city"),
    "Rome, Italy": PlaceCoord(41.9028, 12.4964, "city"),
    "Moscow": PlaceCoord(55.7558, 37.6173, "city"),
    "Toronto, Canada": PlaceCoord(43.6532, -79.3832, "city"),
    "Vancouver, Canada": PlaceCoord(49.2827, -123.1207, "city"),
    "Montreal, Canada": PlaceCoord(45.5017, -73.5673, "city"),
    "Calgary, Canada": PlaceCoord(51.0447, -114.0719, "city"),
    "Markham, ON, Canada": PlaceCoord(43.8561, -79.3370, "city"),
    "Sydney, Australia": PlaceCoord(-33.8688, 151.2093, "city"),
    "Melbourne, Australia": PlaceCoord(-37.8136, 144.9631, "city"),
    "Brisbane, Australia": PlaceCoord(-27.4698, 153.0251, "city"),
    "Perth, Australia": PlaceCoord(-31.9505, 115.8605, "city"),
    "Adelaide, SA, Australia": PlaceCoord(-34.9285, 138.6007, "city"),
    "Tokyo, Japan": PlaceCoord(35.6762, 139.6503, "city"),
    "Osaka, Japan": PlaceCoord(34.6937, 135.5023, "city"),
    "Seoul, South Korea": PlaceCoord(37.5665, 126.9780, "city"),
    "Busan, South Korea": PlaceCoord(35.1796, 129.0756, "city"),
    "Mumbai, India": PlaceCoord(19.0760, 72.8777, "city"),
    "Delhi, India": PlaceCoord(28.7041, 77.1025, "city"),
    "Bangalore, India": PlaceCoord(12.9716, 77.5946, "city"),
    "Dubai, UAE": PlaceCoord(25.2048, 55.2708, "city"),
    "Hong Kong": PlaceCoord(22.3193, 114.1694, "city"),
    "Singapore": PlaceCoord(1.3521, 103.8198, "city"),
    "São Paulo, Brazil": PlaceCoord(-23.5505, -46.6333, "city"),
    "Mexico City, Mexico": PlaceCoord(19.4326, -99.1332, "city"),
    "Buenos Aires, Argentina": PlaceCoord(-34.6037, -58.3816, "city"),

    # --- Countries (too coarse for radius; kept for completeness/future) ---
    "United States": PlaceCoord(39.8283, -98.5795, "country"),
    "United Kingdom": PlaceCoord(54.0, -2.0, "country"),
    "Canada": PlaceCoord(56.1304, -106.3468, "country"),
    "Australia": PlaceCoord(-25.2744, 133.7751, "country"),
    "Japan": PlaceCoord(36.2048, 138.2529, "country"),
    "South Korea": PlaceCoord(35.9078, 127.7669, "country"),
    "France": PlaceCoord(46.2276, 2.2137, "country"),
    "Germany": PlaceCoord(51.1657, 10.4515, "country"),
    "Italy": PlaceCoord(41.8719, 12.5674, "country"),
    "Spain": PlaceCoord(40.4637, -3.7492, "country"),
    "Brazil": PlaceCoord(-14.2350, -51.9253, "country"),
    "Mexico": PlaceCoord(23.6345, -102.5528, "country"),
    "India": PlaceCoord(20.5937, 78.9629, "country"),
    "United Arab Emirates": PlaceCoord(23.4241, 53.8478, "country"),
    "Netherlands": PlaceCoord(52.1326, 5.2913, "country"),
    "Philippines": PlaceCoord(12.8797, 121.7740, "country"),
    "Thailand": PlaceCoord(15.8700, 100.9925, "country"),
    "Vietnam": PlaceCoord(14.0583, 108.2772, "country"),
    "Indonesia": PlaceCoord(-0.7893, 113.9213, "country"),
    "New Zealand": PlaceCoord(-40.9006, 174.8860, "country"),
    "Ireland": PlaceCoord(53.4129, -8.2439, "country"),
    "Sweden": PlaceCoord(60.1282, 18.6435, "country"),
    "Norway": PlaceCoord(60.4720, 8.4689, "country"),
    "Denmark": PlaceCoord(56.2639, 9.5018, "country"),
    "Finland": PlaceCoord(61.9241, 25.7482, "country"),
    "Poland": PlaceCoord(51.9194, 19.1451, "country"),
    "Portugal": PlaceCoord(39.3999, -8.2245, "country"),
    "Switzerland": PlaceCoord(46.8182, 8.2275, "country"),
    "Austria": PlaceCoord(47.5162, 14.5501, "country"),
    "Belgium": PlaceCoord(50.5039, 4.4699, "country"),
    "Greece": PlaceCoord(39.0742, 21.8243, "country"),
    "Nigeria": PlaceCoord(9.0820, 8.6753, "country"),
    "Middle East": PlaceCoord(29.2985, 42.5510, "region"),
}

# Precisions usable for a "within N miles" radius query.
RADIUS_PRECISIONS = ("city", "metro")


def geocode_place(location_text: Optional[str]) -> Optional[PlaceCoord]:
    """Look up coordinates for a location string (canonicalizing first)."""
    if not location_text:
        return None
    value = location_text.strip()
    hit = PLACE_COORDS.get(value)
    if hit:
        return hit
    # Canonicalize variants ("NYC", "Los Angeles") through the location parser.
    from app.utils.location import sanitize_location

    canonical = sanitize_location(value)
    if canonical and canonical != value:
        return PLACE_COORDS.get(canonical)
    return None


def searchable_places() -> list[str]:
    """Place names usable as a radius-search center, alphabetized."""
    return sorted(n for n, c in PLACE_COORDS.items() if c.precision in RADIUS_PRECISIONS)
