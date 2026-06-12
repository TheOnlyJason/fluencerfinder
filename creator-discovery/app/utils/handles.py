import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from app.models.enums import Platform

HANDLE_PATTERN = re.compile(r"^[a-zA-Z0-9._]{1,30}$")


def strip_handle(handle: str) -> str:
    """Remove @ prefix and whitespace from a handle."""
    return handle.strip().lstrip("@").strip()


def normalize_handle(handle: str) -> str:
    """Normalize handle for comparison: lowercase, no @, alphanumeric + ._ only."""
    h = strip_handle(handle).lower()
    h = re.sub(r"[^a-z0-9._]", "", h)
    return h


def compress_handle(handle: str) -> str:
    """Strip separators for cross-platform handle comparison."""
    return re.sub(r"[^a-z0-9]", "", normalize_handle(handle))


def _handle_tokens(handle: str) -> set[str]:
    """Extract meaningful tokens from a handle for cross-platform matching."""
    normalized = normalize_handle(handle)
    tokens = set(normalized.split("_"))
    compressed = compress_handle(handle)
    if compressed:
        tokens.add(compressed)
    # Split camelCase-like boundaries in compressed form
    parts = re.findall(r"[a-z]+", compressed)
    tokens.update(p for p in parts if len(p) >= 2)
    return {t for t in tokens if t}


def handle_similarity(a: str, b: str) -> float:
    """Simple similarity score between two normalized handles."""
    na, nb = normalize_handle(a), normalize_handle(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.85
    ca, cb = compress_handle(a), compress_handle(b)
    if ca and cb:
        if ca == cb:
            return 0.95
        if ca in cb or cb in ca:
            return 0.75
    tokens_a, tokens_b = _handle_tokens(a), _handle_tokens(b)
    if tokens_a and tokens_b:
        shared = tokens_a & tokens_b
        if shared:
            ratio = len(shared) / max(len(tokens_a), len(tokens_b))
            if ratio >= 0.5:
                return max(0.6, ratio)
        # Check if significant tokens from underscored handle appear in compressed form
        underscored = na if "_" in na else nb
        other_compressed = cb if na == underscored else ca
        parts = [p for p in underscored.split("_") if len(p) >= 2]
        if parts and other_compressed:
            hits = sum(1 for p in parts if p in other_compressed)
            if hits >= 2:
                return 0.65
            if hits == 1 and len(parts) <= 2:
                return 0.55
    longer = max(len(na), len(nb))
    if longer == 0:
        return 0.0
    matches = sum(1 for i, c in enumerate(na) if i < len(nb) and nb[i] == c)
    return matches / longer


def parse_profile_url(url: str) -> Tuple[Optional[Platform], Optional[str]]:
    """Extract platform and handle from a profile URL."""
    if not url:
        return None, None
    try:
        parsed = urlparse(url.strip())
        path = parsed.path.strip("/")
        host = (parsed.netloc or "").lower()

        if "instagram.com" in host:
            parts = path.split("/")
            if parts and parts[0] not in ("p", "reel", "stories"):
                return Platform.INSTAGRAM, normalize_handle(parts[0])
        elif "tiktok.com" in host:
            if path.startswith("@"):
                return Platform.TIKTOK, normalize_handle(path[1:].split("/")[0])
            parts = path.split("/")
            if parts and parts[0].startswith("@"):
                return Platform.TIKTOK, normalize_handle(parts[0][1:])
        elif "twitter.com" in host or "x.com" in host:
            parts = path.split("/")
            if parts and parts[0] not in ("i", "intent", "share"):
                return Platform.X, normalize_handle(parts[0])
        elif "youtube.com" in host or "youtu.be" in host:
            if path.startswith("@"):
                return Platform.YOUTUBE, normalize_handle(path[1:].split("/")[0])
            parts = path.split("/")
            if parts and parts[0] == "channel" and len(parts) > 1:
                return Platform.YOUTUBE, parts[1]
            if parts and parts[0] == "user" and len(parts) > 1:
                return Platform.YOUTUBE, normalize_handle(parts[1])
            if parts and parts[0].startswith("@"):
                return Platform.YOUTUBE, normalize_handle(parts[0][1:])
    except Exception:
        pass
    return None, None


def build_profile_url(platform: Platform, handle: str, *, external_links: str | None = None) -> str:
    """Build a canonical profile URL from platform and handle."""
    h = strip_handle(handle)
    if platform == Platform.YOUTUBE:
        from app.utils.youtube import build_youtube_profile_url

        return build_youtube_profile_url(h, external_links=external_links)
    urls = {
        Platform.INSTAGRAM: f"https://www.instagram.com/{h}/",
        Platform.TIKTOK: f"https://www.tiktok.com/@{h}",
        Platform.X: f"https://x.com/{h}",
    }
    return urls.get(platform, f"https://example.com/{h}")


def display_name_similarity(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    na = re.sub(r"[^a-z0-9 ]", "", a.lower()).strip()
    nb = re.sub(r"[^a-z0-9 ]", "", b.lower()).strip()
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.8
    na_words = set(na.split())
    nb_words = set(nb.split())
    if not na_words or not nb_words:
        return 0.0
    overlap = len(na_words & nb_words)
    return overlap / max(len(na_words), len(nb_words))
