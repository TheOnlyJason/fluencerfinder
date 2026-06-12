import re
from typing import Optional

from app.models.enums import Platform

# Match follower/subscriber counts in bios and search snippets (not "following")
_COUNT_PATTERN = re.compile(
    r"(?P<num>[\d,.]+)\s*(?P<suffix>[KkMmBb])?\s*"
    r"(?P<label>followers?|subscribers?)\b",
    re.IGNORECASE,
)


def _parse_number(num: str, suffix: Optional[str]) -> Optional[int]:
    try:
        value = float(num.replace(",", ""))
    except ValueError:
        return None
    if suffix:
        mult = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
        value *= mult.get(suffix.lower(), 1)
    return int(value)


def parse_follower_count(*texts: Optional[str]) -> Optional[int]:
    """Extract the largest follower/subscriber count from text snippets."""
    best: Optional[int] = None
    for text in texts:
        if not text:
            continue
        for match in _COUNT_PATTERN.finditer(text):
            count = _parse_number(match.group("num"), match.group("suffix"))
            if count and count > 0 and (best is None or count > best):
                best = count
    return best


def follower_label(platform: Platform) -> str:
    if platform == Platform.YOUTUBE:
        return "subscribers"
    return "followers"


def format_follower_count(count: Optional[int], platform: Platform) -> Optional[str]:
    if count is None or count <= 0:
        return None
    label = follower_label(platform)
    if count >= 1_000_000:
        value = count / 1_000_000
        return f"{value:.1f}M {label}".replace(".0M", "M")
    if count >= 10_000:
        value = count / 1_000
        return f"{round(value)}K {label}"
    if count >= 1_000:
        value = count / 1_000
        return f"{value:.1f}K {label}".replace(".0K", "K")
    return f"{count:,} {label}"
