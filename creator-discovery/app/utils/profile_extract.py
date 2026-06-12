import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set, Tuple
from urllib.parse import unquote

from app.models.enums import Platform
from app.utils.followers import parse_follower_count
from app.utils.handles import build_profile_url, normalize_handle, parse_profile_url, strip_handle


@dataclass
class ExtractedProfile:
    platform: Platform
    handle: str
    display_name: Optional[str] = None
    profile_url: Optional[str] = None
    bio_text: Optional[str] = None
    follower_count: Optional[int] = None
    source: str = "web_search"

# Path segments that are never creator profile handles
_SKIP_SEGMENTS: dict[Platform, set[str]] = {
    Platform.INSTAGRAM: {
        "p", "reel", "reels", "stories", "explore", "accounts", "popular",
        "direct", "tv", "about", "legal", "developer", "directory",
    },
    Platform.TIKTOK: {
        "discover", "tag", "music", "search", "live", "foryou", "following",
    },
    Platform.X: {
        "i", "intent", "share", "search", "hashtag", "home", "explore", "settings",
    },
    Platform.YOUTUBE: {
        "watch", "playlist", "results", "feed", "shorts", "gaming", "premium",
    },
}


def _is_valid_handle(platform: Platform, handle: str) -> bool:
    if not handle or len(handle) < 2:
        return False
    h = normalize_handle(handle)
    if h in _SKIP_SEGMENTS.get(platform, set()):
        return False
    if platform == Platform.YOUTUBE and h.startswith("uc") and len(h) >= 20:
        return True  # channel id
    if not re.match(r"^[a-z0-9._]+$", h):
        return False
    return True


def profile_from_url(
    url: str,
    *,
    title: Optional[str] = None,
    snippet: Optional[str] = None,
    source: str = "web_search",
) -> Optional[ExtractedProfile]:
    """Parse a search result URL into a profile, if it looks like a creator account."""
    platform, handle = parse_profile_url(url)
    if not platform or not handle or not _is_valid_handle(platform, handle):
        return None
    clean = strip_handle(handle)
    combined_text = " ".join(filter(None, [title, snippet]))
    return ExtractedProfile(
        platform=platform,
        handle=clean,
        display_name=title,
        profile_url=build_profile_url(platform, clean),
        bio_text=snippet,
        follower_count=parse_follower_count(combined_text),
        source=source,
    )


def extract_profiles_from_results(
    results: Iterable[dict],
    *,
    platforms: Optional[List[Platform]] = None,
    source: str = "web_search",
) -> List[ExtractedProfile]:
    """Extract unique creator profiles from search API results."""
    seen: Set[Tuple[Platform, str]] = set()
    accounts: List[ExtractedProfile] = []

    for item in results:
        url = item.get("url") or item.get("link") or item.get("href") or ""
        url = unquote(url)
        account = profile_from_url(
            url,
            title=item.get("title") or item.get("name"),
            snippet=item.get("snippet") or item.get("body") or item.get("content"),
            source=source,
        )
        if not account:
            continue
        if platforms and account.platform not in platforms:
            continue
        key = (account.platform, normalize_handle(account.handle))
        if key in seen:
            continue
        seen.add(key)
        accounts.append(account)

    return accounts
