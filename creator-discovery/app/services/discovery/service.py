import asyncio
import logging
import os
import time
from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select, func

logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, ""))
    except (TypeError, ValueError):
        return default


# Discovery happens inside the HTTP request, so it must finish well under the
# frontend timeout. Cap how much provider work runs per request.
DISCOVER_TIME_BUDGET_S = _env_int("DISCOVER_TIME_BUDGET_S", 35)
DISCOVER_MAX_NEW = _env_int("DISCOVER_MAX_NEW", 12)
DISCOVER_ACCOUNT_TIMEOUT_S = _env_int("DISCOVER_ACCOUNT_TIMEOUT_S", 15)

from app.core.config import get_settings
from app.models.account import Account
from app.models.enums import Platform
from app.schemas.account import AccountRead
from app.schemas.search import ParsedSearchCriteria, SearchRequest, SearchResponse, SearchResultItem
from app.services.classification.classifier import classify_account
from app.services.identity.resolver import attach_or_create_creator, resolve_identity
from app.services.providers.base import DiscoveredAccount, DiscoveryProvider
from app.services.providers.mock_provider import MockDiscoveryProvider
from app.services.embeddings.embedder import build_profile_text, embed_text
from app.utils.fts import search_accounts_fts, sync_account_fts
from app.utils.handles import build_profile_url, normalize_handle, strip_handle
from app.utils.account_metrics import apply_follower_count, resolve_follower_count
from app.utils.vector_search import (
    rrf_fuse,
    semantic_search_accounts,
    store_embedding,
    vector_supported,
)
from app.utils.query_parse import (
    ParsedDiscoveryQuery,
    account_matches_criteria,
    build_discovery_search_queries,
    expand_topic_terms,
    parse_discovery_query,
)


from app.services.providers.web_search_provider import WebSearchDiscoveryProvider
from app.services.providers.youtube_provider import YouTubeDiscoveryProvider


def get_default_providers() -> List[DiscoveryProvider]:
    settings = get_settings()
    providers: List[DiscoveryProvider] = [WebSearchDiscoveryProvider()]
    if settings.youtube_api_key:
        providers.append(YouTubeDiscoveryProvider())
    if settings.use_mock_discovery:
        providers.append(MockDiscoveryProvider())
    return providers


async def _resolve_search_criteria(request: SearchRequest) -> ParsedDiscoveryQuery:
    # Prefer the LLM parser (understands natural language); fall back to regex.
    from app.services.discovery.llm_query_parser import llm_parse_query

    parsed = await llm_parse_query(request.query) or parse_discovery_query(request.query)
    # Explicit request fields (from UI filters) always win over parsed values.
    return ParsedDiscoveryQuery(
        raw_query=request.query,
        topic=request.niche or parsed.topic,
        location=request.location or parsed.location,
        min_followers=request.min_followers if request.min_followers is not None else parsed.min_followers,
        max_followers=request.max_followers if request.max_followers is not None else parsed.max_followers,
        platforms=getattr(parsed, "platforms", None),
        semantic_query=getattr(parsed, "semantic_query", None),
    )


def _criteria_to_schema(criteria: ParsedDiscoveryQuery) -> ParsedSearchCriteria:
    return ParsedSearchCriteria(
        topic=criteria.topic or None,
        location=criteria.location,
        min_followers=criteria.min_followers,
        max_followers=criteria.max_followers,
    )


async def ingest_discovered_account(
    session: Session,
    discovered: DiscoveredAccount,
    *,
    auto_classify: bool = True,
    auto_resolve: bool = True,
) -> Account:
    handle = normalize_handle(discovered.handle)
    existing = session.exec(
        select(Account).where(
            Account.platform == discovered.platform,
            Account.handle == handle,
        )
    ).first()

    profile_url = discovered.profile_url or build_profile_url(discovered.platform, handle)

    if existing:
        existing.display_name = discovered.display_name or existing.display_name
        existing.profile_url = profile_url
        existing.bio_text = discovered.bio_text or existing.bio_text
        existing.location_text = discovered.location_text or existing.location_text
        existing.external_links = discovered.external_links or existing.external_links
        apply_follower_count(existing, discovered)
        existing.last_seen_at = datetime.utcnow()
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        account = existing
    else:
        account = Account(
            platform=discovered.platform,
            handle=handle,
            display_name=discovered.display_name,
            profile_url=profile_url,
            bio_text=discovered.bio_text,
            location_text=discovered.location_text,
            external_links=discovered.external_links,
            follower_count=resolve_follower_count(discovered),
        )
        session.add(account)
        session.commit()
        session.refresh(account)

    if auto_resolve:
        resolution = await resolve_identity(
            session,
            account_id=account.account_id,
        )
        attach_or_create_creator(session, account, resolution)

    if account.platform == Platform.YOUTUBE:
        from app.services.enrichment.youtube_captions import enrich_youtube_captions

        await enrich_youtube_captions(account)

    if auto_classify:
        await classify_account(session, account)

    if not account.follower_count:
        from app.services.enrichment.follower_enrichment import enrich_follower_count

        count = await enrich_follower_count(account, quick=True)
        if count:
            account.follower_count = count

    from app.services.enrichment.profile_enrichment import (
        apply_profile_enrichment,
        enrich_account_profile,
    )

    profile = await enrich_account_profile(account, quick=True)
    apply_profile_enrichment(account, profile)

    sync_account_fts(session, account)
    session.add(account)
    session.commit()
    session.refresh(account)

    # Semantic search embedding (best-effort; Postgres + API key only).
    await store_account_embedding(session, account)
    session.commit()
    return account


async def _ensure_follower_count(account: Account) -> None:
    if account.follower_count:
        return
    from app.services.enrichment.follower_enrichment import enrich_follower_count

    count = await enrich_follower_count(account, quick=False)
    if count:
        account.follower_count = count


def _count_matching_in_database(session: Session, criteria: ParsedDiscoveryQuery) -> int:
    from app.api.routes.accounts import _apply_account_filters

    stmt = select(func.count()).select_from(Account).where(Account.is_active == True)  # noqa: E712
    stmt = _apply_account_filters(
        stmt,
        niches=[criteria.topic] if criteria.topic else None,
        locations=[criteria.location] if criteria.location else None,
        min_followers=criteria.min_followers,
        max_followers=criteria.max_followers,
        is_active=True,
    )
    return session.exec(stmt).one()


def _search_local_db(
    session: Session,
    criteria: ParsedDiscoveryQuery,
    *,
    platforms: Optional[List[Platform]] = None,
    limit: int = 40,
) -> List[Account]:
    search_text = criteria.provider_query or criteria.raw_query
    account_ids = search_accounts_fts(session, search_text, limit=limit * 2)
    accounts: List[Account] = []

    if account_ids:
        for aid in account_ids:
            acc = session.get(Account, aid)
            if acc and acc.is_active:
                accounts.append(acc)
    else:
        stmt = select(Account).where(Account.is_active == True)  # noqa: E712
        if platforms:
            stmt = stmt.where(Account.platform.in_(platforms))
        if criteria.topic:
            from sqlalchemy import or_

            term_clauses = []
            for term in expand_topic_terms(criteria.topic):
                pattern = f"%{term}%"
                term_clauses.append(
                    or_(
                        Account.niche.ilike(pattern),
                        Account.bio_text.ilike(pattern),
                        Account.channel_type.ilike(pattern),
                        Account.hobbies.ilike(pattern),
                    )
                )
            if term_clauses:
                stmt = stmt.where(or_(*term_clauses))
        if criteria.location:
            stmt = stmt.where(Account.location_text.ilike(f"%{criteria.location.split(',')[0]}%"))
        accounts = list(session.exec(stmt.limit(limit * 2)).all())

    filtered: List[Account] = []
    for acc in accounts:
        if platforms and acc.platform not in platforms:
            continue
        if account_matches_criteria(
            acc,
            topic=criteria.topic,
            location=criteria.location,
            min_followers=criteria.min_followers,
            max_followers=criteria.max_followers,
        ):
            filtered.append(acc)

    return filtered[:limit]


def _semantic_query_text(criteria: ParsedDiscoveryQuery) -> str:
    """The phrase we embed to capture search intent.

    Prefer the LLM's cleaned semantic query; otherwise use topic + location;
    finally fall back to the raw query.
    """
    if criteria.semantic_query:
        return criteria.semantic_query
    parts = [criteria.topic] if criteria.topic else []
    if criteria.location:
        parts.append(criteria.location)
    phrase = " ".join(p for p in parts if p).strip()
    return phrase or criteria.raw_query


async def _hybrid_local_search(
    session: Session,
    criteria: ParsedDiscoveryQuery,
    *,
    platforms: Optional[List[Platform]] = None,
    limit: int = 40,
) -> List[Account]:
    """Combine keyword/FTS search with semantic vector search.

    Keyword results give exact-match precision; vector results add semantic
    recall (e.g. "meal prep" matches a "healthy recipes" bio). They're fused
    with Reciprocal Rank Fusion. Falls back to keyword-only when embeddings or
    pgvector aren't available.
    """
    keyword_accounts = _search_local_db(session, criteria, platforms=platforms, limit=limit * 2)

    # Semantic candidates (Postgres + API key only).
    semantic_pairs: List = []
    if vector_supported():
        embedding = await embed_text(_semantic_query_text(criteria))
        if embedding:
            semantic_pairs = semantic_search_accounts(session, embedding, limit=limit * 3)

    if not semantic_pairs:
        # Pure keyword path — already filtered by topic/location/followers.
        return keyword_accounts[:limit]

    keyword_ids = [a.account_id for a in keyword_accounts]
    semantic_ids = [aid for aid, _ in semantic_pairs]
    fused_ids = rrf_fuse(keyword_ids, semantic_ids)

    # Keyword accounts already passed the (keyword) topic filter; semantic ones
    # are matched by meaning, so we only enforce the *hard* structured filters
    # (platform, location, follower range) on them — not the topic keyword.
    keyword_id_set = set(keyword_ids)
    cache = {a.account_id: a for a in keyword_accounts}

    results: List[Account] = []
    for aid in fused_ids:
        acc = cache.get(aid) or session.get(Account, aid)
        if not acc or not acc.is_active:
            continue
        if platforms and acc.platform not in platforms:
            continue
        if aid not in keyword_id_set:
            # Semantic-only hit: apply hard filters but skip the topic keyword check.
            if not account_matches_criteria(
                acc,
                topic=None,
                location=criteria.location,
                min_followers=criteria.min_followers,
                max_followers=criteria.max_followers,
            ):
                continue
        results.append(acc)
        if len(results) >= limit:
            break
    return results


async def store_account_embedding(session: Session, account: Account) -> None:
    """Embed an account's profile and persist the vector (best-effort)."""
    if not vector_supported():
        return
    try:
        embedding = await embed_text(build_profile_text(account))
        if embedding:
            store_embedding(session, account.account_id, embedding)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embedding store failed for %s: %s", account.account_id, exc)


async def search_creators(
    session: Session,
    request: SearchRequest,
    providers: Optional[List[DiscoveryProvider]] = None,
) -> SearchResponse:
    providers = providers or get_default_providers()
    criteria = await _resolve_search_criteria(request)
    # Use platforms the LLM inferred from the text (e.g. "youtubers") when the
    # caller didn't explicitly pass a platform filter.
    effective_platforms = request.platforms
    if not effective_platforms and criteria.platforms:
        effective_platforms = [Platform(p) for p in criteria.platforms if p in {pl.value for pl in Platform}]
    discover_limit = request.limit
    if criteria.has_structured_filters or criteria.topic:
        discover_limit = min(150, max(request.limit * 8, 60))

    # Counted once after discovery below; the pre-discovery count was redundant
    # (it was immediately overwritten) and added a slow round-trip to the DB.
    search_queries = build_discovery_search_queries(criteria)

    local_accounts = await _hybrid_local_search(
        session,
        criteria,
        platforms=effective_platforms,
        limit=discover_limit,
    )
    from_db = len(local_accounts)
    sources: dict = {"database": from_db}

    provider_accounts: List[Account] = []
    from_providers = 0

    if request.use_external_providers:
        seen = {(a.platform, a.handle) for a in local_accounts}
        provider_query = criteria.provider_query or criteria.raw_query
        deadline = time.monotonic() + DISCOVER_TIME_BUDGET_S
        ingested_new = 0
        for provider in providers:
            if ingested_new >= DISCOVER_MAX_NEW or time.monotonic() >= deadline:
                break
            provider_new = 0
            discover_kwargs = {
                "query": provider_query,
                "platforms": effective_platforms,
                # Fetch only a few more than we'll ingest; fetching 150 results is slow.
                "limit": min(discover_limit, max(DISCOVER_MAX_NEW * 3, 30)),
            }
            if getattr(provider, "name", "") == "web_search":
                discover_kwargs["search_queries"] = search_queries
            # Bound discovery by the remaining budget. Without this, a slow
            # provider (web search scrapes many pages at 20-30s each) can run
            # for minutes and blow past the frontend timeout.
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                result = await asyncio.wait_for(
                    provider.discover(**discover_kwargs),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Provider %s discover exceeded time budget (%.0fs)",
                    getattr(provider, "name", provider),
                    DISCOVER_TIME_BUDGET_S,
                )
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("Provider %s discover failed: %s", getattr(provider, "name", provider), exc)
                continue
            for discovered in result.accounts:
                # Stop ingesting once we hit the per-request cap or time budget so
                # the endpoint returns promptly (DB results are already included).
                if ingested_new >= DISCOVER_MAX_NEW or time.monotonic() >= deadline:
                    break
                key = (discovered.platform, normalize_handle(discovered.handle))
                if key in seen:
                    continue
                seen.add(key)
                try:
                    account = await asyncio.wait_for(
                        ingest_discovered_account(session, discovered),
                        timeout=DISCOVER_ACCOUNT_TIMEOUT_S,
                    )
                except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
                    logger.warning("Ingest failed/timed out for %s: %s", discovered.handle, exc)
                    session.rollback()
                    continue
                provider_new += 1
                from_providers += 1
                ingested_new += 1
                if criteria.min_followers is not None or criteria.max_followers is not None:
                    try:
                        await asyncio.wait_for(
                            _ensure_follower_count(account), timeout=DISCOVER_ACCOUNT_TIMEOUT_S
                        )
                    except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                        pass
                if account_matches_criteria(
                    account,
                    topic=criteria.topic,
                    location=criteria.location,
                    min_followers=criteria.min_followers,
                    max_followers=criteria.max_followers,
                ):
                    provider_accounts.append(account)
            if provider_new:
                sources[result.provider_name] = sources.get(result.provider_name, 0) + provider_new

    matched_in_database = _count_matching_in_database(session, criteria)

    all_accounts = local_accounts + provider_accounts
    seen_ids: set[str] = set()
    results: List[SearchResultItem] = []
    for acc in all_accounts:
        if acc.account_id in seen_ids:
            continue
        seen_ids.add(acc.account_id)
        creator_name = None
        if acc.creator_id:
            from app.models.creator import Creator
            creator = session.get(Creator, acc.creator_id)
            if creator:
                creator_name = creator.canonical_name
        source = "database" if acc in local_accounts else "provider"
        results.append(SearchResultItem(
            account=AccountRead.model_validate(acc),
            creator_name=creator_name,
            source=source,
        ))
        if len(results) >= request.limit:
            break

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results),
        sources=sources,
        from_database=from_db,
        from_providers=from_providers,
        matched_in_database=matched_in_database,
        parsed=_criteria_to_schema(criteria),
    )
