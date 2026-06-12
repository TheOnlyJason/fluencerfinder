"""Parse natural-language creator discovery queries into structured filters."""
import re
from dataclasses import dataclass
from typing import List, Optional

from app.utils.location import infer_location

# Related terms so "gamer" matches niche "gaming", etc.
_TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "gamer": ("gamer", "gaming", "game", "games", "esports", "e-sports", "twitch", "streamer", "videogame"),
    "gaming": ("gaming", "gamer", "game", "games", "esports", "twitch", "streamer"),
    "fitness": ("fitness", "gym", "workout", "trainer", "crossfit", "health"),
    "beauty": ("beauty", "makeup", "skincare", "cosmetic", "glam"),
    "food": ("food", "cooking", "chef", "recipe", "culinary"),
    "fashion": ("fashion", "style", "ootd", "outfit"),
    "tech": ("tech", "technology", "developer", "coding", "software"),
    "travel": ("travel", "wanderlust", "adventure", "nomad"),
    "music": ("music", "musician", "artist", "singer", "dj"),
    "comedy": ("comedy", "comedian", "funny", "humor"),
    "tft": ("tft", "teamfight", "tactics", "league", "lol"),
}

_NUM = r"([\d,.]+)\s*([kKmM])?"
_FOLLOWER_WORD = r"(?:followers?|subscribers?|subs?)?"

_MIN_PATTERNS = (
    rf"(?:more\s+than|over|above|at\s+least|minimum|min\.?|>=?)\s+{_NUM}\s*{_FOLLOWER_WORD}",
    rf"(?:greater\s+than)\s+{_NUM}\s*{_FOLLOWER_WORD}",
)
_MAX_PATTERNS = (
    rf"(?:less\s+than|under|below|at\s+most|maximum|max\.?|<=?)\s+{_NUM}\s*{_FOLLOWER_WORD}",
    rf"(?:fewer\s+than)\s+{_NUM}\s*{_FOLLOWER_WORD}",
)
_BETWEEN_PATTERN = re.compile(
    rf"between\s+{_NUM}\s*(?:and|to|-)\s+{_NUM}\s*{_FOLLOWER_WORD}",
    re.I,
)
_RANGE_PATTERN = re.compile(
    rf"{_NUM}\s*(?:to|-|–)\s*{_NUM}\s*{_FOLLOWER_WORD}|"
    rf"{_NUM}-{_NUM}\s*{_FOLLOWER_WORD}?",
    re.I,
)
_LOCATION_IN_PATTERN = re.compile(
    r"\b(?:in|from|based\s+in|near|around|located\s+in)\s+"
    r"([a-zA-Z][a-zA-Z\s,\.'-]{1,40}?)"
    r"(?=\s+(?:that|with|who|having|and|but|,|over|under|more|less|between|\d)|$)",
    re.I,
)
_FILLER_PATTERN = re.compile(
    r"\b(?:that|has|have|with|who|having|but|and|the|a|an|some|any|"
    r"creators?|influencers?|accounts?|people|find|looking\s+for|"
    r"followers?|subscribers?|subs?)\b",
    re.I,
)


@dataclass
class ParsedDiscoveryQuery:
    raw_query: str
    topic: str
    location: Optional[str] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None

    @property
    def provider_query(self) -> str:
        """Search phrase for external discovery providers."""
        parts = []
        if self.topic:
            parts.append(self.topic)
        if self.location:
            parts.append(self.location.split(",")[0])
        if self.min_followers is not None and self.max_followers is not None:
            parts.append(
                f"{_format_count(self.min_followers)} to {_format_count(self.max_followers)} followers"
            )
        elif self.min_followers is not None:
            parts.append(f"{_format_count(self.min_followers)}+ followers")
        elif self.max_followers is not None:
            parts.append(f"under {_format_count(self.max_followers)} followers")
        parts.append("influencer creator")
        return " ".join(parts).strip()

    @property
    def has_structured_filters(self) -> bool:
        return bool(
            self.location
            or self.min_followers is not None
            or self.max_followers is not None
        )


def _format_count(count: int) -> str:
    if count >= 1_000_000:
        v = count / 1_000_000
        return f"{v:.0f}M" if v == int(v) else f"{v:.1f}M"
    if count >= 1_000:
        v = count / 1_000
        return f"{v:.0f}K" if v == int(v) else f"{v:.1f}K"
    return str(count)


def build_discovery_search_queries(criteria: ParsedDiscoveryQuery) -> List[str]:
    """Multiple web search queries to cast a wider net."""
    topic = criteria.topic or ""
    city = (criteria.location or "").split(",")[0].strip()
    base = criteria.provider_query
    queries = [
        base,
        f"{topic} {city} influencer".strip(),
        f"{topic} {city} instagram tiktok youtube creator".strip(),
        f"site:feedspot.com {topic} {city} influencers",
        f"site:collabstr.com {topic} {city}",
        f"{topic} creators {city} followers list",
    ]
    if criteria.min_followers and criteria.max_followers:
        queries.append(
            f"{topic} {city} {_format_count(criteria.min_followers)} {_format_count(criteria.max_followers)} followers"
        )
    seen: set[str] = set()
    out: List[str] = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if len(q) < 4 or q.lower() in seen:
            continue
        seen.add(q.lower())
        out.append(q)
    return out


def expand_topic_terms(topic: Optional[str]) -> List[str]:
    """Expand a topic into related search terms (e.g. gamer → gaming)."""
    if not topic:
        return []
    key = topic.strip().lower()
    if key in _TOPIC_ALIASES:
        return list(dict.fromkeys(_TOPIC_ALIASES[key]))
    for alias_key, terms in _TOPIC_ALIASES.items():
        if key in terms or alias_key in key or key in alias_key:
            return list(dict.fromkeys([key, *terms]))
    words = [w for w in re.split(r"\s+", key) if len(w) >= 3]
    return words or [key]


def _parse_count(num: str, suffix: Optional[str]) -> Optional[int]:
    try:
        value = float(num.replace(",", ""))
    except ValueError:
        return None
    if suffix:
        mult = {"k": 1_000, "m": 1_000_000}
        value *= mult.get(suffix.lower(), 1)
    return int(value)


def _extract_follower_bounds(query: str) -> tuple[str, Optional[int], Optional[int]]:
    working = query
    min_count: Optional[int] = None
    max_count: Optional[int] = None

    between = _BETWEEN_PATTERN.search(working)
    if between:
        min_count = _parse_count(between.group(1), between.group(2))
        max_count = _parse_count(between.group(3), between.group(4))
        working = working[: between.start()] + working[between.end() :]

    range_match = _RANGE_PATTERN.search(working)
    if range_match:
        if range_match.lastindex and range_match.lastindex >= 4:
            lo_num, lo_suf = range_match.group(1), range_match.group(2)
            hi_num, hi_suf = range_match.group(3), range_match.group(4)
        else:
            lo_num, lo_suf = range_match.group(1), range_match.group(2)
            hi_num, hi_suf = range_match.group(3), range_match.group(4)
        if min_count is None:
            min_count = _parse_count(lo_num, lo_suf)
        if max_count is None:
            max_count = _parse_count(hi_num, hi_suf)
        working = working[: range_match.start()] + working[range_match.end() :]

    for pattern in _MIN_PATTERNS:
        match = re.search(pattern, working, re.I)
        if match:
            min_count = _parse_count(match.group(1), match.group(2))
            working = working[: match.start()] + working[match.end() :]
            break

    for pattern in _MAX_PATTERNS:
        match = re.search(pattern, working, re.I)
        if match:
            max_count = _parse_count(match.group(1), match.group(2))
            working = working[: match.start()] + working[match.end() :]
            break

    return working, min_count, max_count


def _extract_location(query: str) -> tuple[str, Optional[str]]:
    match = _LOCATION_IN_PATTERN.search(query)
    if match:
        fragment = match.group(1).strip(" ,.'")
        location = infer_location(fragment) or infer_location(query)
        cleaned = query[: match.start()] + " " + query[match.end() :]
        if location:
            return cleaned, location

    location = infer_location(query)
    if location:
        return query, location

    return query, None


def _extract_topic(query: str) -> str:
    topic = _FILLER_PATTERN.sub(" ", query)
    topic = re.sub(r"\s+", " ", topic).strip(" ,.-")
    return topic


def parse_discovery_query(query: str) -> ParsedDiscoveryQuery:
    """Turn a free-text query into topic, location, and follower bounds."""
    raw = query.strip()
    working = raw

    working, min_followers, max_followers = _extract_follower_bounds(working)
    working, location = _extract_location(working)
    topic = _extract_topic(working)

    if not topic and raw:
        topic = _extract_topic(raw)

    return ParsedDiscoveryQuery(
        raw_query=raw,
        topic=topic,
        location=location,
        min_followers=min_followers,
        max_followers=max_followers,
    )


def account_matches_criteria(
    account,
    *,
    topic: Optional[str] = None,
    location: Optional[str] = None,
    min_followers: Optional[int] = None,
    max_followers: Optional[int] = None,
) -> bool:
    """Return True if an account satisfies parsed discovery criteria."""
    if min_followers is not None:
        if account.follower_count is None or account.follower_count < min_followers:
            return False
    if max_followers is not None:
        if account.follower_count is None or account.follower_count > max_followers:
            return False

    if location:
        loc = (account.location_text or "").lower()
        bio = (account.bio_text or "").lower()
        needle = location.lower()
        if needle not in loc and needle not in bio:
            # Allow partial city match e.g. "Los Angeles" matches "Los Angeles, CA"
            city = needle.split(",")[0].strip()
            if city not in loc and city not in bio:
                return False

    if topic:
        terms = expand_topic_terms(topic)
        text = " ".join(
            filter(
                None,
                [
                    account.handle,
                    account.display_name,
                    account.bio_text,
                    account.niche,
                    account.channel_type,
                    account.hobbies,
                    account.secondary_niches,
                ],
            )
        ).lower()
        if not any(term in text for term in terms):
            return False

    return True
