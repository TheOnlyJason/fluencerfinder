from typing import List, Optional

import httpx

from app.core.config import get_settings
from app.models.enums import Platform
from app.services.providers.base import DiscoveredAccount, DiscoveryProvider, DiscoveryResult
from app.utils.handles import normalize_handle, strip_handle
from app.utils.location import iso_country_name
from app.utils.youtube import build_youtube_profile_url


class YouTubeDiscoveryProvider(DiscoveryProvider):
    """Discover YouTube channels via the YouTube Data API v3."""

    name = "youtube_api"

    async def discover(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        limit: int = 20,
    ) -> DiscoveryResult:
        settings = get_settings()
        if platforms and Platform.YOUTUBE not in platforms:
            return DiscoveryResult(accounts=[], provider_name=self.name, query=query)
        if not settings.youtube_api_key:
            return DiscoveryResult(accounts=[], provider_name=self.name, query=query)

        search_query = f"{query} creator"
        async with httpx.AsyncClient(timeout=30.0) as client:
            search_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "type": "channel",
                    "q": search_query,
                    "maxResults": min(limit, 25),
                    "key": settings.youtube_api_key,
                },
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            if not items:
                return DiscoveryResult(accounts=[], provider_name=self.name, query=query)

            channel_ids = [
                item["id"]["channelId"]
                for item in items
                if item.get("id", {}).get("channelId")
            ]
            if not channel_ids:
                return DiscoveryResult(accounts=[], provider_name=self.name, query=query)

            channels_resp = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "part": "snippet,statistics",
                    "id": ",".join(channel_ids),
                    "key": settings.youtube_api_key,
                },
            )
            channels_resp.raise_for_status()
            channel_map = {
                ch["id"]: ch for ch in channels_resp.json().get("items", [])
            }

        accounts: List[DiscoveredAccount] = []
        for item in items:
            channel_id = item.get("id", {}).get("channelId")
            if not channel_id or channel_id not in channel_map:
                continue
            ch = channel_map[channel_id]
            snippet = ch.get("snippet", {})
            stats = ch.get("statistics", {})
            subscriber_count = None
            if stats.get("subscriberCount"):
                try:
                    subscriber_count = int(stats["subscriberCount"])
                except (TypeError, ValueError):
                    pass
            custom_url = snippet.get("customUrl") or ""
            handle = strip_handle(custom_url.lstrip("@")) if custom_url else channel_id
            if not handle:
                continue
            accounts.append(
                DiscoveredAccount(
                    platform=Platform.YOUTUBE,
                    handle=normalize_handle(handle) if not handle.startswith("UC") else handle,
                    display_name=snippet.get("title"),
                    profile_url=build_youtube_profile_url(
                        strip_handle(handle),
                        channel_id=channel_id,
                    ),
                    bio_text=snippet.get("description", "")[:500] or None,
                    # snippet.country is a documented ISO alpha-2 code — here
                    # "CA" really is Canada, so translate at the source rather
                    # than letting free-text sanitization guess (or drop) it.
                    location_text=iso_country_name(snippet.get("country"))
                    or snippet.get("country"),
                    follower_count=subscriber_count,
                    source=self.name,
                )
            )

        return DiscoveryResult(
            accounts=accounts[:limit],
            provider_name=self.name,
            query=query,
        )
