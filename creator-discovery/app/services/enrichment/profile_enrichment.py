import logging
from dataclasses import dataclass
from typing import List, Optional

from app.models.account import Account
from app.models.enums import Platform
from app.services.enrichment.web_search import search_delay, search_web
from app.utils.contact import parse_email
from app.utils.location import infer_location, is_valid_location, sanitize_location

logger = logging.getLogger(__name__)

_PLATFORM_SITES = {
    Platform.INSTAGRAM: "instagram.com",
    Platform.TIKTOK: "tiktok.com",
    Platform.X: "x.com",
    Platform.YOUTUBE: "youtube.com",
}


@dataclass
class ProfileEnrichment:
    location: Optional[str] = None
    contact_email: Optional[str] = None


def _profile_queries(account: Account) -> List[str]:
    handle = account.handle.lstrip("@")
    site = _PLATFORM_SITES.get(account.platform, "")
    return [
        f"{site} @{handle} bio email contact",
        f"@{handle} {account.platform.value} creator based in location",
        f"{account.display_name or handle} influencer contact email",
    ]


def _infer_from_texts(account: Account, texts: List[str]) -> ProfileEnrichment:
    email = parse_email(*texts)
    location = infer_location(*texts, handle=account.handle)
    if not location and account.location_text:
        location = infer_location(account.location_text, handle=account.handle)
    return ProfileEnrichment(location=location, contact_email=email)


async def enrich_account_profile(account: Account, *, quick: bool = False) -> ProfileEnrichment:
    """Fill missing location and email from bio, links, and web search — no LLM."""
    texts = [
        account.bio_text,
        account.display_name,
        account.external_links,
        account.location_text,
    ]

    result = _infer_from_texts(account, list(filter(None, texts)))
    if result.contact_email and result.location:
        return result
    if quick and (result.contact_email or result.location):
        return result

    search_texts: List[str] = list(filter(None, texts))
    queries = _profile_queries(account)
    if quick:
        queries = queries[:1]

    for query in queries:
        results = await search_web(query, max_results=5)
        for r in results:
            combined = f"{r['title']} {r['snippet']}"
            search_texts.append(combined)
        inferred = _infer_from_texts(account, search_texts)
        if not result.contact_email and inferred.contact_email:
            result.contact_email = inferred.contact_email
        if not result.location and inferred.location:
            result.location = inferred.location
        if result.contact_email and result.location:
            break
        if not quick:
            await search_delay(0.3)

    return result


def apply_profile_enrichment(account: Account, enriched: ProfileEnrichment) -> bool:
    changed = False
    location = sanitize_location(enriched.location)
    if location and (not account.location_text or not is_valid_location(account.location_text)):
        if account.location_text != location:
            account.location_text = location
            changed = True
    if enriched.contact_email and not account.contact_email:
        account.contact_email = enriched.contact_email
        changed = True
    return changed
