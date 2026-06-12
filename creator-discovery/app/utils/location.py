"""Approximate location inference from public profile text — no LLM required."""
import re
from typing import Iterable, Optional

# Canonical place names (longer phrases first when matching)
_PLACES: tuple[tuple[str, str], ...] = (
    ("southern california", "Southern California"),
    ("los angeles", "Los Angeles, CA"),
    ("san francisco", "San Francisco, CA"),
    ("san diego", "San Diego, CA"),
    ("new york city", "New York, NY"),
    ("new york", "New York, NY"),
    ("las vegas", "Las Vegas, NV"),
    ("salt lake city", "Salt Lake City, UT"),
    ("kansas city", "Kansas City, MO"),
    ("san antonio", "San Antonio, TX"),
    ("fort worth", "Fort Worth, TX"),
    ("silicon valley", "San Francisco Bay Area, CA"),
    ("bay area", "San Francisco Bay Area, CA"),
    ("beverly hills", "Los Angeles, CA"),
    ("miami beach", "Miami, FL"),
    ("hong kong", "Hong Kong"),
    ("são paulo", "São Paulo, Brazil"),
    ("sao paulo", "São Paulo, Brazil"),
    ("mexico city", "Mexico City, Mexico"),
    ("buenos aires", "Buenos Aires, Argentina"),
    ("santa monica", "Los Angeles, CA"),
    ("west hollywood", "Los Angeles, CA"),
    ("manhattan", "New York, NY"),
    ("brooklyn", "New York, NY"),
    ("queens", "New York, NY"),
    ("soho", "New York, NY"),
    ("hollywood", "Los Angeles, CA"),
    ("socal", "Southern California"),
    ("nyc", "New York, NY"),
    ("atlanta", "Atlanta, GA"),
    ("austin", "Austin, TX"),
    ("boston", "Boston, MA"),
    ("chicago", "Chicago, IL"),
    ("dallas", "Dallas, TX"),
    ("denver", "Denver, CO"),
    ("detroit", "Detroit, MI"),
    ("houston", "Houston, TX"),
    ("london", "London, UK"),
    ("manchester", "Manchester, UK"),
    ("birmingham", "Birmingham, UK"),
    ("edinburgh", "Edinburgh, UK"),
    ("paris", "Paris, France"),
    ("berlin", "Berlin, Germany"),
    ("munich", "Munich, Germany"),
    ("amsterdam", "Amsterdam, Netherlands"),
    ("barcelona", "Barcelona, Spain"),
    ("madrid", "Madrid, Spain"),
    ("milan", "Milan, Italy"),
    ("rome", "Rome, Italy"),
    ("toronto", "Toronto, Canada"),
    ("vancouver", "Vancouver, Canada"),
    ("montreal", "Montreal, Canada"),
    ("calgary", "Calgary, Canada"),
    ("sydney", "Sydney, Australia"),
    ("melbourne", "Melbourne, Australia"),
    ("brisbane", "Brisbane, Australia"),
    ("perth", "Perth, Australia"),
    ("tokyo", "Tokyo, Japan"),
    ("osaka", "Osaka, Japan"),
    ("seoul", "Seoul, South Korea"),
    ("busan", "Busan, South Korea"),
    ("singapore", "Singapore"),
    ("dubai", "Dubai, UAE"),
    ("mumbai", "Mumbai, India"),
    ("delhi", "Delhi, India"),
    ("bangalore", "Bangalore, India"),
    ("california", "California"),
    ("florida", "Florida"),
    ("texas", "Texas"),
    ("colorado", "Colorado"),
    ("arizona", "Arizona"),
    ("georgia", "Georgia"),
    ("hawaii", "Hawaii"),
    ("miami", "Miami, FL"),
    ("seattle", "Seattle, WA"),
    ("portland", "Portland, OR"),
    ("phoenix", "Phoenix, AZ"),
    ("philadelphia", "Philadelphia, PA"),
    ("nashville", "Nashville, TN"),
    ("orlando", "Orlando, FL"),
    ("tampa", "Tampa, FL"),
    ("minneapolis", "Minneapolis, MN"),
    ("charlotte", "Charlotte, NC"),
    ("raleigh", "Raleigh, NC"),
    ("pittsburgh", "Pittsburgh, PA"),
    ("cleveland", "Cleveland, OH"),
    ("columbus", "Columbus, OH"),
    ("indianapolis", "Indianapolis, IN"),
    ("baltimore", "Baltimore, MD"),
    ("dc", "Washington, DC"),
    ("washington dc", "Washington, DC"),
    ("scottsdale", "Phoenix, AZ"),
    ("honolulu", "Honolulu, HI"),
)

# Words that are not place names when captured after "from"
_REJECT_LEAD_WORDS = frozenset({
    "the", "their", "my", "your", "our", "this", "that", "these", "those",
    "a", "an", "all", "every", "any", "some", "enter", "watch", "click",
    "subscribe", "follow", "check", "link", "bio", "dm", "email", "contact",
    "video", "videos", "content", "post", "posts", "phone", "smartphone",
    "smartphones", "iphone", "android", "youtube", "tiktok", "instagram",
})

# Sports teams, landmarks, and venues → city
_LOCALE_HINTS: tuple[tuple[str, str], ...] = (
    ("lakers", "Los Angeles, CA"),
    ("clippers", "Los Angeles, CA"),
    ("dodgers", "Los Angeles, CA"),
    ("rams", "Los Angeles, CA"),
    ("chargers", "Los Angeles, CA"),
    ("yankees", "New York, NY"),
    ("mets", "New York, NY"),
    ("knicks", "New York, NY"),
    ("nets", "New York, NY"),
    ("giants", "New York, NY"),
    ("warriors", "San Francisco, CA"),
    ("49ers", "San Francisco Bay Area, CA"),
    ("celtics", "Boston, MA"),
    ("patriots", "Boston, MA"),
    ("bulls", "Chicago, IL"),
    ("cubs", "Chicago, IL"),
    ("cowboys", "Dallas, TX"),
    ("mavericks", "Dallas, TX"),
    ("heat", "Miami, FL"),
    ("marlins", "Miami, FL"),
    ("falcons", "Atlanta, GA"),
    ("braves", "Atlanta, GA"),
    ("rockies", "Denver, CO"),
    ("nuggets", "Denver, CO"),
    ("times square", "New York, NY"),
    ("wall street", "New York, NY"),
    ("central park", "New York, NY"),
    ("venice beach", "Los Angeles, CA"),
    ("santa monica pier", "Los Angeles, CA"),
    ("griffith observatory", "Los Angeles, CA"),
    ("ucla", "Los Angeles, CA"),
    ("usc", "Los Angeles, CA"),
    ("nyu", "New York, NY"),
    ("columbia university", "New York, NY"),
    ("stanford", "San Francisco Bay Area, CA"),
    ("berkeley", "San Francisco Bay Area, CA"),
    ("harvard", "Boston, MA"),
    ("mit", "Boston, MA"),
    ("coachella", "Southern California"),
    ("vegas strip", "Las Vegas, NV"),
)

_FLAG_COUNTRY = {
    "🇺🇸": "United States",
    "🇬🇧": "United Kingdom",
    "🇨🇦": "Canada",
    "🇦🇺": "Australia",
    "🇯🇵": "Japan",
    "🇰🇷": "South Korea",
    "🇫🇷": "France",
    "🇩🇪": "Germany",
    "🇮🇹": "Italy",
    "🇪🇸": "Spain",
    "🇧🇷": "Brazil",
    "🇲🇽": "Mexico",
    "🇮🇳": "India",
    "🇦🇪": "United Arab Emirates",
    "🇸🇬": "Singapore",
    "🇳🇱": "Netherlands",
    "🇵🇭": "Philippines",
    "🇹🇭": "Thailand",
    "🇻🇳": "Vietnam",
    "🇮🇩": "Indonesia",
}

_ISO_COUNTRY = {
    "US": "United States",
    "USA": "United States",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "JP": "Japan",
    "KR": "South Korea",
    "FR": "France",
    "DE": "Germany",
    "IT": "Italy",
    "ES": "Spain",
    "BR": "Brazil",
    "MX": "Mexico",
    "IN": "India",
    "AE": "United Arab Emirates",
    "SG": "Singapore",
    "NL": "Netherlands",
    "PH": "Philippines",
    "TH": "Thailand",
    "VN": "Vietnam",
    "ID": "Indonesia",
    "NZ": "New Zealand",
    "IE": "Ireland",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "PL": "Poland",
    "PT": "Portugal",
    "CH": "Switzerland",
    "AT": "Austria",
    "BE": "Belgium",
}

# US area code → metro (approximate)
_AREA_CODES: dict[str, str] = {
    "213": "Los Angeles, CA",
    "310": "Los Angeles, CA",
    "323": "Los Angeles, CA",
    "424": "Los Angeles, CA",
    "818": "Los Angeles, CA",
    "212": "New York, NY",
    "646": "New York, NY",
    "718": "New York, NY",
    "917": "New York, NY",
    "415": "San Francisco, CA",
    "628": "San Francisco, CA",
    "305": "Miami, FL",
    "786": "Miami, FL",
    "312": "Chicago, IL",
    "773": "Chicago, IL",
    "214": "Dallas, TX",
    "469": "Dallas, TX",
    "713": "Houston, TX",
    "281": "Houston, TX",
    "404": "Atlanta, GA",
    "678": "Atlanta, GA",
    "617": "Boston, MA",
    "857": "Boston, MA",
    "206": "Seattle, WA",
    "425": "Seattle, WA",
    "702": "Las Vegas, NV",
    "480": "Phoenix, AZ",
    "602": "Phoenix, AZ",
    "303": "Denver, CO",
    "720": "Denver, CO",
    "512": "Austin, TX",
    "737": "Austin, TX",
    "615": "Nashville, TN",
    "202": "Washington, DC",
}

_EXPLICIT_PATTERNS = [
    re.compile(
        r"(?:based in|located in|living in|lives in|📍|🌍|🌎|🌏)\s*([^|,\n\r\.#@\"]{2,40})",
        re.I,
    ),
    re.compile(r"\bfrom\s+([A-Z][a-zA-Z\s\-']+(?:,\s*[A-Z]{2,3})?)\b"),
    re.compile(
        r"([A-Z][a-zA-Z\s]+,\s*(?:CA|NY|TX|FL|GA|IL|CO|AZ|WA|OR|MA|PA|OH|NC|TN|NV|UT|MO|HI|UK|USA|US|Japan|Canada|Australia|France|Germany|Spain|Italy|Brazil|Mexico))\b"
    ),
]

_REJECT_LOCATION_RE = re.compile(
    r"@|\.com|\.org|\.net|https?://|www\.|\d{4}|"
    r'["\']|enter to win|giveaway|subscribe|follow me|packed wi|smartphone|'
    r"\(\@|tweet|retweet|youtube\.com|tiktok\.com|instagram\.com|"
    r"\btiktok\b|\bgaming\b|grin about|adopted|product updates",
    re.I,
)

_HASHTAG_LOCATION = re.compile(r"#([a-z]{2,20})(?:\b|(?=[A-Z]))", re.I)
_PHONE_AREA = re.compile(r"\b(?:\+1[-.\s]?)?\(?(\d{3})\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

_HANDLE_HINTS = {
    "nyc": "New York, NY",
    "la": "Los Angeles, CA",
    "lax": "Los Angeles, CA",
    "socal": "Southern California",
    "sf": "San Francisco, CA",
    "atl": "Atlanta, GA",
    "chi": "Chicago, IL",
    "dfw": "Dallas, TX",
    "miami": "Miami, FL",
    "vegas": "Las Vegas, NV",
    "london": "London, UK",
    "tokyo": "Tokyo, Japan",
    "seoul": "Seoul, South Korea",
}

_CANONICAL_VALUES = frozenset(
    {canonical for _, canonical in _PLACES}
    | {canonical for _, canonical in _LOCALE_HINTS}
    | set(_FLAG_COUNTRY.values())
    | set(_ISO_COUNTRY.values())
    | set(_HANDLE_HINTS.values())
    | set(_AREA_CODES.values())
)


def is_valid_location(loc: Optional[str]) -> bool:
    """Return True if the string looks like a real geographic location."""
    if not loc:
        return False
    loc = loc.strip()
    if len(loc) < 2 or len(loc) > 35:
        return False
    if _REJECT_LOCATION_RE.search(loc):
        return False
    if loc in _CANONICAL_VALUES:
        return True
    if _match_places(loc):
        return True
    first = loc.split()[0].lower().rstrip(".,;:")
    if first in _REJECT_LEAD_WORDS:
        return False
    words = loc.split()
    # City, ST or City, Country
    if re.match(
        r"^[A-Z][a-zA-Z\s\-']+,\s*[A-Z]{2,3}(?:,\s*[A-Z][a-zA-Z\s]+)?$",
        loc,
    ):
        return True
    # Multi-word names must be in our place dictionary (e.g. Southern California)
    if len(words) >= 2:
        return False
    # Single-word city/region names
    if len(words) == 1 and re.match(r"^[A-Z][a-zA-Z\-']+$", loc):
        if _match_places(loc):
            return True
        return len(loc) >= 6
    return False


def sanitize_location(loc: Optional[str]) -> Optional[str]:
    """Normalize and validate a location string; return None if invalid."""
    if not loc:
        return None
    cleaned = loc.strip().strip("\"'")
    if not is_valid_location(cleaned):
        return None
    known = _match_places(cleaned)
    if known:
        return known
    if cleaned in _CANONICAL_VALUES:
        return cleaned
    return cleaned


def _contains_phrase(text: str, phrase: str) -> bool:
    if len(phrase) <= 3:
        return bool(re.search(rf"\b{re.escape(phrase)}\b", text, re.I))
    return phrase.lower() in text.lower()


def _match_places(text: str) -> Optional[str]:
    for needle, canonical in _PLACES:
        if _contains_phrase(text, needle):
            return canonical
    return None


def _match_locale_hints(text: str) -> Optional[str]:
    lower = text.lower()
    for needle, canonical in _LOCALE_HINTS:
        if needle in lower:
            return canonical
    return None


def _match_explicit(text: str) -> Optional[str]:
    for pattern in _EXPLICIT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        fragment = match.group(1).strip()
        place = _match_places(fragment)
        if place:
            return place
        sanitized = sanitize_location(fragment)
        if sanitized:
            return sanitized
    return None


def _clean_explicit_fragment(fragment: str) -> Optional[str]:
    fragment = re.sub(
        r"\s+(sharing|creating|making|posting|content|videos?|daily).*$",
        "",
        fragment,
        flags=re.I,
    )
    fragment = fragment.strip(" -•|\"'")
    place = _match_places(fragment)
    if place:
        return place
    return sanitize_location(fragment)


def _match_hashtags(text: str) -> Optional[str]:
    for match in _HASHTAG_LOCATION.finditer(text):
        tag = match.group(1).lower()
        for needle, canonical in _PLACES:
            if tag == needle.replace(" ", "") or tag == needle.replace(" ", "_"):
                return canonical
        if tag in _HANDLE_HINTS:
            return _HANDLE_HINTS[tag]
    return None


def _match_flags(text: str) -> Optional[str]:
    for flag, country in _FLAG_COUNTRY.items():
        if flag in text:
            return country
    return None


def _match_area_code(text: str) -> Optional[str]:
    match = _PHONE_AREA.search(text)
    if match:
        return _AREA_CODES.get(match.group(1))
    return None


def _match_iso_country(text: str) -> Optional[str]:
    stripped = text.strip()
    if len(stripped) == 2 and stripped.upper() in _ISO_COUNTRY:
        return _ISO_COUNTRY[stripped.upper()]
    match = re.search(
        r"(?:country|nation|based in|located in)\s*:?\s*([A-Z]{2})\b",
        text,
        re.I,
    )
    if match:
        code = match.group(1).upper()
        if code in _ISO_COUNTRY:
            return _ISO_COUNTRY[code]
    return None


def _match_handle(handle: Optional[str]) -> Optional[str]:
    if not handle:
        return None
    tokens = re.split(r"[_\-.]", handle.lower().lstrip("@"))
    for token in tokens:
        if token in _HANDLE_HINTS:
            return _HANDLE_HINTS[token]
        place = _match_places(token)
        if place:
            return place
    return None


def _match_script_region(text: str) -> Optional[str]:
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text):
        if _contains_phrase(text, "tokyo") or _contains_phrase(text, "osaka"):
            return _match_places(text)
        return "Japan"
    if re.search(r"[\uac00-\ud7af]", text):
        if _contains_phrase(text, "seoul") or _contains_phrase(text, "busan"):
            return _match_places(text)
        return "South Korea"
    if re.search(r"[\u0600-\u06ff]", text):
        return "Middle East"
    return None


def infer_location(
    *texts: Optional[str],
    handle: Optional[str] = None,
) -> Optional[str]:
    """Infer approximate location from bios, search snippets, handles, etc."""
    combined_parts: list[str] = []
    for text in texts:
        if text:
            combined_parts.append(text)
    if not combined_parts and not handle:
        return None

    combined = " ".join(combined_parts)
    candidates: list[Optional[str]] = []

    for text in combined_parts:
        candidates.append(_match_explicit(text))

    candidates.append(_match_places(combined))
    candidates.append(_match_hashtags(combined))
    candidates.append(_match_locale_hints(combined))
    candidates.append(_match_handle(handle))
    candidates.append(_match_flags(combined))
    candidates.append(_match_area_code(combined))

    for text in combined_parts:
        candidates.append(_match_iso_country(text))

    candidates.append(_match_script_region(combined))

    for candidate in candidates:
        sanitized = sanitize_location(candidate)
        if sanitized:
            return sanitized

    return None


def parse_location(*texts: Optional[str]) -> Optional[str]:
    """Backward-compatible alias."""
    return infer_location(*texts)
