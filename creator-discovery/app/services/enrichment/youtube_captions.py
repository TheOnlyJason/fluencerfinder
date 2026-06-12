"""YouTube caption-based niche enrichment using recent video transcripts."""
import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

import httpx

from app.core.config import get_settings
from app.models.account import Account
from app.models.enums import Platform
from app.utils.query_parse import expand_topic_terms

logger = logging.getLogger(__name__)

_ATOM_NS = {"yt": "http://www.youtube.com/xml/schemas/2015", "atom": "http://www.w3.org/2005/Atom"}

_CAPTION_NICHE_KEYWORDS = {
    "gaming": ("game", "gaming", "gamer", "playthrough", "minecraft", "fortnite", "esports", "stream"),
    "fitness": ("workout", "fitness", "gym", "exercise", "training", "muscle", "cardio"),
    "beauty": ("makeup", "beauty", "skincare", "cosmetic", "grwm", "foundation", "lipstick"),
    "food": ("recipe", "cooking", "food", "meal prep", "kitchen", "bake", "chef"),
    "tech": ("tech", "technology", "review", "unbox", "smartphone", "laptop", "gadget"),
    "travel": ("travel", "trip", "vacation", "hotel", "flight", "adventure", "destination"),
    "fashion": ("outfit", "fashion", "style", "ootd", "wardrobe", "haul"),
    "music": ("music", "song", "album", "concert", "cover", "remix"),
    "comedy": ("comedy", "funny", "skit", "prank", "laugh"),
}


def parse_youtube_channel_id(account: Account) -> Optional[str]:
    links = account.external_links or ""
    match = re.search(r"youtube_channel_id=([A-Za-z0-9_-]+)", links)
    if match:
        return match.group(1)
    if account.handle and account.handle.upper().startswith("UC"):
        return account.handle
    return None


def infer_niche_from_caption_text(text: str) -> Optional[str]:
    """Keyword-based niche guess from caption/bio text."""
    lower = text.lower()
    best_niche: Optional[str] = None
    best_score = 0
    for niche, terms in _CAPTION_NICHE_KEYWORDS.items():
        score = sum(1 for term in terms if term in lower)
        if score > best_score:
            best_score = score
            best_niche = niche
    return best_niche if best_score >= 2 else None


def _fetch_transcript_sync(video_id: str) -> Optional[str]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        return " ".join(item.text for item in fetched.snippets[:250])
    except Exception as exc:
        logger.debug("Transcript fetch failed for %s: %s", video_id, exc)
        return None


async def _resolve_channel_id(client: httpx.AsyncClient, account: Account, api_key: str) -> Optional[str]:
    existing = parse_youtube_channel_id(account)
    if existing:
        return existing

    handle = account.handle.lstrip("@")
    if handle.upper().startswith("UC"):
        return handle

    for param, value in (("forHandle", handle), ("forUsername", handle)):
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "id", param: value, "key": api_key},
        )
        if resp.status_code != 200:
            continue
        items = resp.json().get("items", [])
        if items:
            return items[0]["id"]

    search = await client.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "type": "channel",
            "q": handle,
            "maxResults": 1,
            "key": api_key,
        },
    )
    if search.status_code == 200:
        items = search.json().get("items", [])
        if items:
            return items[0].get("id", {}).get("channelId")
    return None


async def _video_ids_from_rss(
    client: httpx.AsyncClient,
    channel_id: str,
    *,
    limit: int = 3,
) -> List[str]:
    """Fetch recent upload video IDs via public YouTube RSS (no API key)."""
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    resp = await client.get(url, follow_redirects=True)
    if resp.status_code != 200:
        return []
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return []
    ids: List[str] = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        vid = entry.find("yt:videoId", _ATOM_NS)
        if vid is not None and vid.text:
            ids.append(vid.text)
        if len(ids) >= limit:
            break
    return ids


async def _recent_video_ids(
    client: httpx.AsyncClient,
    channel_id: str,
    api_key: Optional[str],
    *,
    limit: int = 3,
) -> List[str]:
    if not api_key:
        return await _video_ids_from_rss(client, channel_id, limit=limit)

    ch_resp = await client.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "contentDetails", "id": channel_id, "key": api_key},
    )
    if ch_resp.status_code != 200:
        return await _video_ids_from_rss(client, channel_id, limit=limit)
    items = ch_resp.json().get("items", [])
    if not items:
        return await _video_ids_from_rss(client, channel_id, limit=limit)
    uploads = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads:
        return await _video_ids_from_rss(client, channel_id, limit=limit)

    pl_resp = await client.get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        params={
            "part": "contentDetails",
            "playlistId": uploads,
            "maxResults": limit,
            "key": api_key,
        },
    )
    if pl_resp.status_code != 200:
        return await _video_ids_from_rss(client, channel_id, limit=limit)
    return [
        item["contentDetails"]["videoId"]
        for item in pl_resp.json().get("items", [])
        if item.get("contentDetails", {}).get("videoId")
    ] or await _video_ids_from_rss(client, channel_id, limit=limit)


async def fetch_youtube_caption_context(account: Account, *, max_videos: int = 3) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch recent video transcript text and inferred niche for a YouTube account.
    Returns (caption_text, inferred_niche).
    """
    if account.platform != Platform.YOUTUBE:
        return None, None

    settings = get_settings()
    api_key = settings.youtube_api_key or None

    async with httpx.AsyncClient(timeout=30.0) as client:
        channel_id = parse_youtube_channel_id(account)
        if not channel_id and api_key:
            channel_id = await _resolve_channel_id(client, account, api_key)
        if not channel_id:
            return None, None

        video_ids = await _recent_video_ids(
            client, channel_id, api_key, limit=max_videos
        )

    texts: List[str] = []
    for vid in video_ids:
        transcript = await asyncio.to_thread(_fetch_transcript_sync, vid)
        if transcript:
            texts.append(transcript)

    if not texts:
        return None, None

    combined = " ".join(texts)[:4000]
    niche = infer_niche_from_caption_text(combined)
    return combined, niche


async def enrich_youtube_captions(account: Account) -> bool:
    """Append caption context to bio and set niche when confident."""
    caption_text, niche = await fetch_youtube_caption_context(account)
    if not caption_text:
        return False

    snippet = caption_text[:1500]
    marker = "YouTube video topics:"
    if marker not in (account.bio_text or ""):
        prefix = account.bio_text or account.display_name or ""
        account.bio_text = f"{prefix}\n\n{marker} {snippet}".strip()

    channel_id = parse_youtube_channel_id(account)
    if channel_id and "youtube_channel_id=" not in (account.external_links or ""):
        links = account.external_links or ""
        account.external_links = f"youtube_channel_id={channel_id}; {links}".strip("; ")

    if niche and (not account.niche or account.niche == "unknown"):
        account.niche = niche
        account.channel_type = niche

    if niche:
        terms = expand_topic_terms(niche)
        if terms and not account.hobbies:
            account.hobbies = ", ".join(terms[:4])

    return True
