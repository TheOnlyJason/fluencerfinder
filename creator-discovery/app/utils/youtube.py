"""YouTube handle and channel ID helpers."""
import re
from typing import Optional

from app.models.enums import Platform
from app.utils.handles import strip_handle

_CHANNEL_ID_RE = re.compile(r"^UC[a-zA-Z0-9_-]{20,}$", re.IGNORECASE)
_YOUTUBE_URL_RE = re.compile(
    r"https?://(?:www\.)?youtube\.com/(?:user|channel|c)/[^\s;]+",
    re.IGNORECASE,
)


def is_youtube_channel_id(value: Optional[str]) -> bool:
    if not value:
        return False
    cleaned = value.strip().lstrip("@")
    return bool(_CHANNEL_ID_RE.match(cleaned))


def parse_youtube_channel_id(external_links: Optional[str]) -> Optional[str]:
    if not external_links:
        return None
    match = re.search(r"youtube_channel_id=([A-Za-z0-9_-]+)", external_links)
    if match:
        return match.group(1)
    return None


def find_stored_youtube_url(external_links: Optional[str]) -> Optional[str]:
    """Return a canonical YouTube profile URL stored in external_links."""
    if not external_links:
        return None
    for part in external_links.split(";"):
        part = part.strip()
        if _YOUTUBE_URL_RE.match(part):
            return part.rstrip("/")
    return None


def build_youtube_profile_url(
    handle: str,
    *,
    channel_id: Optional[str] = None,
    external_links: Optional[str] = None,
) -> str:
    """
    Build a working YouTube profile URL.

    Prefers stored /user/ or /channel/ links, then channel ID, then /user/{handle}.
    Legacy channels often use /user/ rather than /@handle.
    """
    stored = find_stored_youtube_url(external_links)
    if stored:
        return stored

    cid = channel_id or parse_youtube_channel_id(external_links)
    if cid:
        return f"https://www.youtube.com/channel/{cid}"

    return f"https://www.youtube.com/user/{strip_handle(handle)}"


def slugify_youtube_handle(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    slug = re.sub(r"[^a-z0-9._]", "", name.lower())
    return slug or None


def format_display_handle(
    platform: Platform,
    handle: str,
    display_name: Optional[str] = None,
) -> str:
    """Return a human-readable handle for UI display."""
    if platform == Platform.YOUTUBE and is_youtube_channel_id(handle):
        slug = slugify_youtube_handle(display_name)
        if slug:
            return slug
    return handle.lstrip("@")
