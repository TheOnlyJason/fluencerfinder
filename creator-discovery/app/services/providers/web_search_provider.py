import asyncio
import logging
import re
from typing import List, Optional, Set, Tuple

import httpx

from app.core.config import get_settings
from app.models.enums import Platform
from app.services.providers.base import DiscoveredAccount, DiscoveryProvider, DiscoveryResult
from app.utils.handles import build_profile_url, normalize_handle
from app.utils.profile_extract import extract_profiles_from_results, profile_from_url

logger = logging.getLogger(__name__)

_PLATFORM_HINTS = {
    Platform.INSTAGRAM: "instagram.com",
    Platform.TIKTOK: "tiktok.com",
    Platform.X: "x.com",
    Platform.YOUTUBE: "youtube.com",
    Platform.TWITCH: "twitch.tv",
}

# Domains that aggregate influencer lists — scrape for profile links
_LISTICLE_DOMAINS = (
    "feedspot.com",
    "influencers.feedspot.com",
    "modash.io",
    "collabstr.com",
    "hypeauditor.com",
)

_SOCIAL_URL_PATTERNS = {
    Platform.INSTAGRAM: re.compile(
        r"https?://(?:www\.)?instagram\.com/([a-zA-Z0-9._]+)/?", re.I
    ),
    Platform.TIKTOK: re.compile(
        r"https?://(?:www\.)?tiktok\.com/@([a-zA-Z0-9._]+)/?", re.I
    ),
    Platform.X: re.compile(
        r"https?://(?:www\.)?(?:x|twitter)\.com/([a-zA-Z0-9_]+)/?", re.I
    ),
    Platform.YOUTUBE: re.compile(
        r"https?://(?:www\.)?youtube\.com/@([a-zA-Z0-9._-]+)/?", re.I
    ),
    Platform.TWITCH: re.compile(
        r"https?://(?:www\.)?twitch\.tv/([a-zA-Z0-9_]{3,25})/?", re.I
    ),
}


class WebSearchDiscoveryProvider(DiscoveryProvider):
    """Find real public creator profiles via web search (Tavily or DuckDuckGo)."""

    name = "web_search"

    async def discover(
        self,
        query: str,
        platforms: Optional[List[Platform]] = None,
        limit: int = 20,
        search_queries: Optional[List[str]] = None,
    ) -> DiscoveryResult:
        target_platforms = platforms or list(Platform)
        per_platform = max(12, limit // max(len(target_platforms), 1) + 8)
        all_accounts: List[DiscoveredAccount] = []
        seen: Set[Tuple[Platform, str]] = set()

        base_queries = search_queries or [query]
        for platform in target_platforms:
            # .get() so a platform added to the enum without a hint here skips
            # (a hard KeyError used to kill discovery for ALL platforms).
            hint = _PLATFORM_HINTS.get(platform)
            if hint is None:
                continue
            platform_results: List[dict] = []
            queries_for_platform = list(dict.fromkeys(
                [f"{hint} {q}" for q in base_queries]
                + [f"{q} {platform.value} creator profile" for q in base_queries[:3]]
            ))
            for sq in queries_for_platform:
                platform_results.extend(await self._run_search(sq, max_results=per_platform))
                if len(platform_results) >= per_platform * 2:
                    break

            # Direct profile URLs from search results
            for extracted in extract_profiles_from_results(
                platform_results, platforms=[platform], source=self.name
            ):
                self._add_account(all_accounts, seen, extracted, platform)

            # Scrape influencer list pages for embedded profile links
            listicle_urls = [
                r.get("url") or r.get("href") or r.get("link")
                for r in platform_results
                if any(d in (r.get("url") or r.get("href") or r.get("link") or "") for d in _LISTICLE_DOMAINS)
            ]
            for page_url in listicle_urls[:4]:
                if page_url:
                    scraped = await self._scrape_profiles_from_page(page_url, platform)
                    for extracted in scraped:
                        self._add_account(all_accounts, seen, extracted, platform)

        return DiscoveryResult(
            accounts=all_accounts[:limit],
            provider_name=self.name,
            query=query,
        )

    def _add_account(
        self,
        accounts: List[DiscoveredAccount],
        seen: Set[Tuple[Platform, str]],
        extracted,
        platform: Platform,
    ) -> None:
        if extracted.platform != platform:
            return
        key = (extracted.platform, normalize_handle(extracted.handle))
        if key in seen:
            return
        seen.add(key)
        accounts.append(
            DiscoveredAccount(
                platform=extracted.platform,
                handle=extracted.handle,
                display_name=extracted.display_name,
                profile_url=extracted.profile_url or build_profile_url(extracted.platform, extracted.handle),
                bio_text=extracted.bio_text,
                follower_count=extracted.follower_count,
                source=self.name,
            )
        )

    async def _scrape_profiles_from_page(
        self, url: str, platform: Platform
    ) -> List:
        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CreatorDiscovery/1.0)"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.debug("Could not scrape %s: %s", url, exc)
            return []

        pattern = _SOCIAL_URL_PATTERNS.get(platform)
        if not pattern:
            return []

        profiles = []
        for match in pattern.finditer(html):
            handle = match.group(1)
            account = profile_from_url(
                match.group(0),
                source=self.name,
            )
            if account and account.platform == platform:
                profiles.append(account)
        return profiles

    async def _run_search(self, query: str, max_results: int) -> List[dict]:
        settings = get_settings()
        if settings.tavily_api_key:
            try:
                return await self._search_tavily(query, max_results)
            except Exception as exc:
                logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", exc)
        return await self._search_duckduckgo(query, max_results)

    async def _search_tavily(self, query: str, max_results: int) -> List[dict]:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                {
                    "url": r.get("url"),
                    "href": r.get("url"),
                    "title": r.get("title"),
                    "snippet": r.get("content"),
                }
                for r in data.get("results", [])
            ]

    async def _search_duckduckgo(self, query: str, max_results: int) -> List[dict]:
        def _sync_search() -> List[dict]:
            try:
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS

                with DDGS() as ddgs:
                    raw = list(ddgs.text(query, max_results=max_results))
                return [
                    {
                        "url": r.get("href") or r.get("link"),
                        "href": r.get("href") or r.get("link"),
                        "title": r.get("title"),
                        "snippet": r.get("body") or r.get("snippet"),
                    }
                    for r in raw
                ]
            except Exception as exc:
                logger.error("DuckDuckGo search failed: %s", exc)
                return []

        return await asyncio.to_thread(_sync_search)
