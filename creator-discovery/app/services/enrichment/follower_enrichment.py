import asyncio
import logging
from typing import List, Optional

from app.models.account import Account
from app.models.enums import Platform
from app.services.enrichment.web_search import search_delay, search_web
from app.utils.followers import parse_follower_count

logger = logging.getLogger(__name__)

_PLATFORM_SITES = {
    Platform.INSTAGRAM: "instagram.com",
    Platform.TIKTOK: "tiktok.com",
    Platform.X: "x.com",
    Platform.YOUTUBE: "youtube.com",
}


def _enrichment_queries(account: Account) -> List[str]:
    handle = account.handle.lstrip("@")
    site = _PLATFORM_SITES.get(account.platform, "")
    queries = [
        f"@{handle} {account.platform.value} followers",
        f"{site} @{handle} followers",
    ]
    if account.platform == Platform.TIKTOK:
        queries.insert(0, f"tiktok.com/@{handle} followers")
    elif account.platform == Platform.INSTAGRAM:
        queries.insert(0, f"instagram.com/{handle} followers")
    elif account.platform == Platform.X:
        queries.insert(0, f"x.com/{handle} followers")
    elif account.platform == Platform.YOUTUBE:
        queries.insert(0, f"youtube.com/@{handle} subscribers")
    return queries


async def enrich_follower_count(account: Account, *, quick: bool = False) -> Optional[int]:
    """Look up follower/subscriber count via web search when bio is missing."""
    from_bio = parse_follower_count(account.bio_text, account.display_name)
    if from_bio:
        return from_bio

    queries = _enrichment_queries(account)
    if quick:
        queries = queries[:1]

    for query in queries:
        results = await search_web(query, max_results=6)
        texts = [f"{r['title']} {r['snippet']}" for r in results]
        count = parse_follower_count(*texts)
        if count:
            return count
        if not quick:
            await search_delay(0.3)

    return None


async def enrich_accounts_followers(
    accounts: List[Account],
    *,
    only_missing: bool = True,
    refresh_stale: bool = False,
    max_accounts: Optional[int] = None,
) -> int:
    updated = 0

    def _needs_refresh(account: Account) -> bool:
        if not account.follower_count:
            return True
        if not refresh_stale:
            return False
        if account.follower_count < 1_000:
            return True
        links = account.external_links or ""
        if account.platform == Platform.INSTAGRAM and "source=rightfluencer" in links:
            return True
        return False

    targets = [a for a in accounts if _needs_refresh(a)]
    if max_accounts:
        targets = targets[:max_accounts]

    for account in targets:
        count = await enrich_follower_count(account)
        if count and (not account.follower_count or count > account.follower_count):
            account.follower_count = count
            updated += 1
        await search_delay(0.4)

    return updated
